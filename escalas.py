import streamlit as st
import sqlite3
import datetime
import pandas as pd
import ast
import random
import smtplib
from email.mime.text import MIMEText
from fpdf import FPDF
import banco
import escalas
import requests  # Importado para fazer o disparo HTTP para o n8n


# =====================================================================
# 📚 REFERÊNCIA TÉCNICA — PONTOS DE CORTE DA LITERATURA
# =====================================================================
# Usado no PDF pra dar ao profissional uma comparação rápida entre o
# resultado do paciente e o que a literatura estabelece como referência,
# sem precisar consultar outra fonte na hora da tomada de decisão.
# Chave = mesmo texto-base salvo em "tipo" na tabela avaliacoes (antes do
# parêntese), pra bater automaticamente com o histórico de cada paciente.
REFERENCIAS_LITERATURA = {
    "Mini-Exame do Estado Mental": {
        "corte": "Ponto de corte varia por escolaridade: Analfabeto 20 | 1-4 anos 25 | "
        "5-8 anos 26 | 9-11 anos 28 | Superior 29 (de 30 pontos).",
        "citacao": "Folstein et al. (1975); Brucki et al. (2003) - padronização brasileira",
    },
    "Teste do Desenho do Relógio": {
        "corte": "Pontuação 4/4 (círculo, números e ponteiros corretos) sugere função "
        "executiva/visuoespacial preservada; escores menores indicam alteração.",
        "citacao": "Sunderland et al. (1989); Nitrini et al. (2004)",
    },
    "Timed Up and Go": {
        "corte": "<10s: mobilidade normal | 10-20s: risco moderado de quedas | "
        ">20s: alto risco, indica avaliação funcional mais aprofundada.",
        "citacao": "Podsiadlo & Richardson (1991)",
    },
    "Índice de Katz": {
        "corte": "6 pontos: independência total | 3-5: dependência parcial | "
        "≤2: dependência grave para Atividades Básicas de Vida Diária (ABVD).",
        "citacao": "Katz et al. (1963)",
    },
    "Escala de Lawton e Brody": {
        "corte": "Faixa de 8-24 pontos (Atividades Instrumentais de Vida Diária): quanto "
        "maior, maior a independência para tarefas complexas do dia a dia.",
        "citacao": "Lawton & Brody (1969); Santos & Virtuoso (2008) - adaptação brasileira",
    },
    "Escala de Depressao Geriatrica": {
        "corte": "0-5: sem sintomas depressivos | 6-10: sugestivo de depressão leve a "
        "moderada | >10: sugestivo de depressão grave (escala de 15 itens).",
        "citacao": "Yesavage et al. (1983); Almeida & Almeida (1999) - validação brasileira",
    },
    "Escala Zarit-22": {
        "corte": "0-20: pouca ou nenhuma sobrecarga | 21-40: sobrecarga leve a moderada | "
        "41-60: moderada a severa | 61-88: sobrecarga severa do cuidador.",
        "citacao": "Zarit et al. (1980); Scazufca (2002) - validação brasileira",
    },
    "Triagem Inicial": {
        "corte": "IMC do idoso (Lipschitz): <22 baixo peso | 22-27 eutrofia | >27 "
        "sobrepeso. Panturrilha <31cm sugere risco de sarcopenia (OPAS).",
        "citacao": "Lipschitz (1994); Organização Pan-Americana da Saúde (OPAS)",
    },
}


# NOTA: a função disparar_webhook_n8n que efetivamente funciona no app fica
# em escalas.py (chamada por escalas.salvar_avaliacao a cada escala salva).
# Havia uma segunda versão dela aqui, com uma assinatura de parâmetros
# diferente, que nunca chegava a ser chamada de verdade - só código morto
# de uma iteração anterior. Removida pra não confundir manutenção futura.


def renderizar_configuracoes_integracao(clinica_id):
    st.success(
        "📲 O compartilhamento no WhatsApp já funciona automaticamente em cada "
        "avaliação salva. Pra abrir direto na conversa certa (em vez de escolher "
        "o contato manualmente toda vez), cadastre o número na ficha do paciente "
        "- campo 'WhatsApp para receber os resultados', na aba Novo Idoso ou em "
        "Evolução & Prontuários."
    )
    st.subheader("🔗 Automação avançada com n8n (opcional)")
    st.markdown(
        "Só preencha isto se sua clínica já usa **n8n** para automatizar fluxos "
        "(disparo automático sem intervenção manual, integração com outros sistemas etc). "
        "A maioria dos profissionais não precisa disso — o botão de WhatsApp de cada "
        "avaliação já resolve o compartilhamento do dia a dia."
    )

    # Busca configuração existente no banco
    conn = sqlite3.connect("gerontodata.db")
    cursor = conn.cursor()
    # Garante que a tabela exista antes de consultar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS integracoes_clinica (
            clinica_id INTEGER PRIMARY KEY,
            url_webhook_n8n TEXT
        )
    """)
    cursor.execute(
        "SELECT url_webhook_n8n FROM integracoes_clinica WHERE clinica_id = ?",
        (clinica_id,),
    )
    linha = cursor.fetchone()
    url_atual = linha[0] if linha else ""
    conn.close()

    # Input para o usuário colar a URL
    nova_url = st.text_input(
        "URL do Webhook do n8n (deixe em branco se não usa):",
        value=url_atual,
        placeholder="https://seu-n8n.com/webhook/...",
    )

    if st.button("💾 Salvar Integração"):
        conn = sqlite3.connect("gerontodata.db")
        cursor = conn.cursor()
        # Faz um UPSERT (insere ou atualiza se já existir)
        cursor.execute(
            """
            INSERT INTO integracoes_clinica (clinica_id, url_webhook_n8n)
            VALUES (?, ?)
            ON CONFLICT(clinica_id) DO UPDATE SET url_webhook_n8n = excluded.url_webhook_n8n
        """,
            (clinica_id, nova_url),
        )
        conn.commit()
        conn.close()
        st.success("Configuração de integração salva com sucesso!")
        st.rerun()


# --- INTERFACE VISUAL (RESTANTE DO SEU CÓDIGO PRESERVADO) ---
#
# NOTA: havia aqui um bloco de navegação antigo (sidebar "pagina" com
# dashboard/pacientes/nova_avaliacao/configuracoes/feedback) que:
#   1) rodava ANTES da tela de login, sem checar autenticação — qualquer
#      pessoa via o dashboard e cadastrava pacientes sem logar;
#   2) chamava st.set_page_config() uma segunda vez logo abaixo, o que
#      derruba o Streamlit com StreamlitAPIException (só pode chamar 1x).
# Esse bloco era código legado que ficou duplicado com o fluxo novo baseado
# em abas (menu_principal, mais abaixo, já protegido pelo login). Removido.


def renderizar_aba_feedback(usuario_email):
    """Desenha a interface visual do formulário de feedback"""
    st.markdown("### 📬 Central de Feedback & Suporte")
    st.write(
        "Sua opinião é fundamental para evoluirmos a plataforma. Use o espaço abaixo para relatar bugs, sugerir melhorias ou fazer críticas."
    )

    with st.form("form_suporte_feedback", clear_on_submit=True):
        tipo_mensagem = st.selectbox(
            "Tipo de Ocorrência",
            [
                "Sugestão de Melhoria",
                "Relatar um Bug / Erro",
                "Dúvida Técnica",
                "Crítica / Elogio",
            ],
        )

        detalhes = st.text_area(
            "Descrição detalhada:",
            placeholder="Conte-nos detalhadamente o que aconteceu ou o que gostaria de ver no sistema...",
        )

        botao_enviar = st.form_submit_button("Enviar Mensagem")

        if botao_enviar:
            if detalhes.strip() == "":
                st.error("❌ Por favor, descreva o seu feedback antes de enviar.")
            else:
                try:
                    conn = sqlite3.connect("gerontodata.db")
                    cursor = conn.cursor()
                    data_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                    cursor.execute(
                        "INSERT INTO feedbacks (email, tipo, mensagem, data) VALUES (?, ?, ?, ?)",
                        (usuario_email, tipo_mensagem, detalhes, data_atual),
                    )
                    conn.commit()
                    conn.close()

                    st.success(
                        "✅ Ocorrência registrada com sucesso! Nossa equipe técnica analisará o seu caso."
                    )
                except Exception as e:
                    st.error(f"Erro crítico ao salvar no banco: {e}")


# Configuração da identidade do App
st.set_page_config(
    page_title="GerontoData Beta 1.0",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inicializa banco expandido
banco.criar_tabelas()

# =====================================================================
# 🎨 SISTEMA DE DESIGN — GERONTODATA
# =====================================================================
# Paleta: verde-petróleo profundo (confiança clínica, sem cair no laranja
# genérico nem no visual "IA padrão"). Cor de risco (âmbar/vermelho) é usada
# SÓ para sinalizar resultados clínicos (ex: risco de queda), nunca como cor
# de marca — assim o olho aprende a associar essas cores só a alerta real.
#
#   --cor-primaria:      #1F4B44  (verde-petróleo escuro - marca, títulos, botões)
#   --cor-primaria-hover:#163832  (mais escuro - hover/pressed)
#   --cor-destaque-dado: #4C7A6D  (verde-sálvia - links, números secundários)
#   --cor-fundo:         #F3F5F3  (cinza-esverdeado bem claro - fundo geral)
#   --cor-superficie:    #FFFFFF  (cards, inputs)
#   --cor-texto:         #1B231F  (quase preto, tom quente)
#   --cor-texto-suave:   #5B6B64  (legendas, texto secundário)
#   --cor-borda:         #DCE3DE
#   --cor-risco-baixo:   #3E7C59  (verde - normal/independente)
#   --cor-risco-medio:   #C97B2E  (âmbar - risco moderado/alerta)
#   --cor-risco-alto:    #A23B3B  (vermelho-tijolo - risco alto/dependência)
#
# Tipografia:
#   Títulos:      "Source Serif 4"  (serifada, dá peso institucional/clínico)
#   Corpo/UI:     "IBM Plex Sans"   (limpa, legível em formulários)
#   Dados/escores:"IBM Plex Mono"   (números de avaliação clínica -
#                                    reforça precisão/leitura de dado)
st.markdown(
    """
    <link rel="icon" href="data:image/svg+xml;base64,PHN2ZyB2aWV3Qm94PSIwIDAgNjQgNjQiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PGxpbmVhckdyYWRpZW50IGlkPSJnIiB4MT0iMCUiIHkxPSIwJSIgeDI9IjEwMCUiIHkyPSIxMDAlIj48c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjMUY0QjQ0Ii8+PHN0b3Agb2Zmc2V0PSIxMDAlIiBzdG9wLWNvbG9yPSIjNEM3QTZEIi8+PC9saW5lYXJHcmFkaWVudD48L2RlZnM+PGNpcmNsZSBjeD0iMzIiIGN5PSIzMiIgcj0iMzAiIGZpbGw9InVybCgjZykiLz48cGF0aCBkPSJNMzIgNDVjLTguNS02LjItMTUtMTEuNi0xNS0xOWE5LjUgOS41IDAgMCAxIDE3LTUuOEE5LjUgOS41IDAgMCAxIDUxIDI2YzAgNy40LTYuNSAxMi44LTE1IDE5eiIgZmlsbD0iI0ZGRkZGRiIgb3BhY2l0eT0iMC45NiIvPjwvc3ZnPgo=" type="image/svg+xml">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --cor-primaria: #1F4B44;
            --cor-primaria-hover: #163832;
            --cor-destaque-dado: #4C7A6D;
            --cor-fundo: #F3F5F3;
            --cor-superficie: #FFFFFF;
            --cor-texto: #1B231F;
            --cor-texto-suave: #5B6B64;
            --cor-borda: #DCE3DE;
            --cor-risco-baixo: #3E7C59;
            --cor-risco-medio: #C97B2E;
            --cor-risco-alto: #A23B3B;
        }

        /* 1. EXTINÇÃO DA BARRA SUPERIOR E MENUS NATIVOS */
        [data-testid="stHeader"], header, .stActionButton, [data-testid="stDecoration"] {
            display: none !important;
        }

        /* 2. FUNDO E TEXTO BASE - gradiente sutil, não plano */
        .stApp, [data-testid="stAppViewContainer"] {
            background: linear-gradient(160deg, #EEF3F0 0%, #F3F5F3 22%, #F6F7F5 55%, #EFF4F1 100%) !important;
            color: var(--cor-texto) !important;
        }
        [data-testid="stMainBlockContainer"], [data-testid="stForm"] {
            background-color: var(--cor-fundo) !important;
            color: var(--cor-texto) !important;
        }

        p, span, label, li, th, td, div, small, [data-testid="stMarkdownContainer"] p {
            color: var(--cor-texto) !important;
            font-family: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }

        /* Os ícones nativos do Streamlit (setas, engrenagem, hamburger etc.) são
           desenhados por uma fonte de ícones (Material Symbols): o texto do span
           (ex: "arrow_back") só vira desenho por causa dessa fonte. A regra acima
           forçava outra fonte em TODO span, então o ícone quebrava e aparecia
           como texto cru sobreposto ao label. Esta regra devolve a fonte de
           ícone só para eles. */
        [data-testid*="Icon"],
        [data-testid="stIconMaterial"],
        span[class*="material-symbols"] {
            font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: "Source Serif 4", Georgia, serif !important;
            color: var(--cor-primaria) !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em !important;
        }

        /* Valores/escores numéricos (ex: pontuação de escalas) ganham a fonte
           mono quando marcados com a classe .dado-clinico (ver badge_risco). */
        .dado-clinico {
            font-family: "IBM Plex Mono", "Courier New", monospace !important;
            font-weight: 600 !important;
        }

        /* 3. CAMPOS DE SELEÇÃO (SELECTBOX) */
        div[data-baseweb="select"],
        div[data-baseweb="select"] > div,
        [data-testid="stSelectbox"] div,
        [data-testid="stSelectbox"] aria-box,
        .stSelectbox > div {
            background-color: var(--cor-superficie) !important;
            color: var(--cor-texto) !important;
            border-color: var(--cor-borda) !important;
        }

        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div,
        [data-testid="stSelectbox"] p,
        .stSelectbox span,
        .stSelectbox div {
            color: var(--cor-texto) !important;
        }

        input, textarea, select, .stTextArea textarea, div[data-baseweb="base-input"] > input {
            background-color: var(--cor-superficie) !important;
            color: var(--cor-texto) !important;
            border: 1px solid var(--cor-borda) !important;
            border-radius: 8px !important;
        }
        input:focus, textarea:focus, div[data-baseweb="base-input"]:focus-within {
            border-color: var(--cor-primaria) !important;
            box-shadow: 0 0 0 1px var(--cor-primaria) !important;
        }

        /* 4. MENUS SUSPENSOS (POPOVERS) */
        div[role="listbox"],
        ul[role="listbox"],
        li[role="option"],
        [data-baseweb="menu"],
        [data-baseweb="popover"],
        div[data-baseweb="popover"] * {
            background-color: var(--cor-superficie) !important;
            color: var(--cor-texto) !important;
        }
        li[role="option"] div, li[role="option"] span {
            color: var(--cor-texto) !important;
            background-color: var(--cor-superficie) !important;
        }
        li[role="option"]:hover, li[role="option"]:hover div {
            background-color: #EAF0EC !important;
            color: var(--cor-primaria) !important;
        }

        div[data-testid="stNumberInput"] button {
            background-color: var(--cor-primaria) !important;
            color: #FFFFFF !important;
        }

        /* 5. BOTÕES */
        @media (min-width: 768px) {
            div.stButton > button, [data-testid="stFormSubmitButton"] button { width: auto !important; min-width: 200px !important; padding: 10px 24px !important; display: inline-block !important; }
        }
        @media (max-width: 767px) {
            div.stButton > button, [data-testid="stFormSubmitButton"] button { width: 100% !important; padding: 14px 20px !important; font-size: 16px !important; display: block !important; }
            button[data-baseweb="tab"] { padding: 10px 12px !important; font-size: 14px !important; }
        }

        button, [data-testid="stFormSubmitButton"] button {
            background: linear-gradient(135deg, #266157 0%, #1F4B44 55%, #163832 100%) !important;
            color: #FFFFFF !important;
            border-radius: 10px !important;
            border: none !important;
            font-family: "IBM Plex Sans", sans-serif !important;
            font-weight: 600 !important;
            box-shadow: 0 2px 8px rgba(31, 75, 68, 0.28) !important;
            transition: transform 0.12s ease, box-shadow 0.12s ease, background 0.15s ease !important;
        }
        button:hover, [data-testid="stFormSubmitButton"] button:hover {
            background: linear-gradient(135deg, #2E7267 0%, #235347 55%, #163832 100%) !important;
            box-shadow: 0 5px 14px rgba(31, 75, 68, 0.38) !important;
            transform: translateY(-1px) !important;
        }
        button:active, [data-testid="stFormSubmitButton"] button:active {
            transform: translateY(0) !important;
            box-shadow: 0 2px 6px rgba(31, 75, 68, 0.3) !important;
        }

        /* 6. CARDS */
        .medical-card {
            position: relative !important;
            background: linear-gradient(180deg, #FFFFFF 0%, #FCFDFC 100%) !important;
            border: 1px solid var(--cor-borda) !important;
            border-left: none !important;
            border-radius: 12px !important;
            padding: 16px 16px 16px 20px !important;
            margin-bottom: 12px !important;
            box-shadow: 0 2px 10px rgba(27, 35, 31, 0.07) !important;
            transition: box-shadow 0.15s ease, transform 0.15s ease !important;
            overflow: hidden !important;
        }
        .medical-card::before {
            content: "" !important;
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            bottom: 0 !important;
            width: 5px !important;
            background: linear-gradient(180deg, #2E7267, #1F4B44) !important;
        }
        .medical-card:hover {
            box-shadow: 0 6px 18px rgba(27, 35, 31, 0.12) !important;
            transform: translateY(-1px) !important;
        }

        /* 7. SELOS DE RISCO CLÍNICO (usados junto com badge_risco()) */
        .selo-risco {
            display: inline-block;
            font-family: "IBM Plex Sans", sans-serif;
            font-size: 12px;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 999px;
            letter-spacing: 0.02em;
        }
        .selo-risco.baixo  { background-color: #E4F0E9; color: var(--cor-risco-baixo); }
        .selo-risco.medio  { background-color: #FBEBDA; color: var(--cor-risco-medio); }
        .selo-risco.alto   { background-color: #F6E1E1; color: var(--cor-risco-alto); }

        /* 8. ABAS — estilo "segmented control" em vez de linha simples */
        [data-baseweb="tab-list"] {
            background-color: #E9EFEB !important;
            border-radius: 999px !important;
            padding: 4px !important;
            gap: 4px !important;
        }
        button[data-baseweb="tab"] {
            background-color: transparent !important;
            color: var(--cor-texto-suave) !important;
            font-family: "IBM Plex Sans", sans-serif !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            border: none !important;
            border-radius: 999px !important;
            box-shadow: none !important;
            transition: background 0.15s ease, color 0.15s ease !important;
        }
        button[aria-selected="true"] {
            background: linear-gradient(135deg, #266157 0%, #1F4B44 100%) !important;
            color: #FFFFFF !important;
            border-bottom: none !important;
            box-shadow: 0 2px 6px rgba(31, 75, 68, 0.28) !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def badge_risco(nivel, texto):
    """
    Selo colorido consistente pra qualquer resultado clínico com risco:
    nivel = 'baixo' | 'medio' | 'alto'. Usar em qualquer tela com
    st.markdown(badge_risco(...), unsafe_allow_html=True).
    """
    classe = nivel if nivel in ("baixo", "medio", "alto") else "medio"
    return f'<span class="selo-risco {classe}">{texto}</span>'


# =====================================================================
# 📄 MOTOR DO PDF CLÍNICO (COMPLETO E CORRIGIDO)
# =====================================================================
def gerar_pdf_historico(
    df_filtrado,
    nome_paciente,
    idade_paciente,
    sexo_paciente,
    dados_paciente=None,
    dados_prof=None,
):
    pdf = FPDF()
    pdf.set_title("Prontuário Gerontológico Multidimensional")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    def p(texto):
        # Garante que caracteres especiais funcionem no PDF
        return (
            str(texto)
            .replace("—", "-")
            .replace("•", "-")
            .encode("cp1252", "ignore")
            .decode("cp1252")
        )

    def quebrar_texto(texto, largura_disponivel):
        """
        Quebra o texto em linhas que cabem na largura da coluna, usando só
        get_string_width/cell/rect - métodos estáveis e antigos do fpdf2,
        pra não depender de parâmetros mais novos que podem variar entre
        versões (e que não dá pra testar sem instalar a biblioteca aqui).
        """
        palavras = texto.split(" ")
        linhas = []
        linha_atual = ""
        for palavra in palavras:
            tentativa = (linha_atual + " " + palavra).strip()
            if pdf.get_string_width(tentativa) <= largura_disponivel - 2:
                linha_atual = tentativa
            else:
                if linha_atual:
                    linhas.append(linha_atual)
                linha_atual = palavra
        if linha_atual:
            linhas.append(linha_atual)
        return linhas if linhas else [""]

    def celula_tabela(
        larguras, textos, altura_linha=5, alinhamentos=None, preenchido=False
    ):
        """
        Desenha uma 'linha de tabela' quebrando o texto manualmente em
        linhas que cabem na coluna (era isso que faltava: texto longo vazava
        pra fora da célula porque cell() não quebra linha). Todas as colunas
        da linha ficam com a mesma altura (a da maior célula).
        """
        if alinhamentos is None:
            alinhamentos = ["L"] * len(textos)

        x_inicial = pdf.get_x()
        y_inicial = pdf.get_y()

        linhas_colunas = [
            quebrar_texto(t, largura) for t, largura in zip(textos, larguras)
        ]
        n_linhas = max(len(linhas) for linhas in linhas_colunas)
        altura_total = n_linhas * altura_linha

        # Quebra de página manual se a linha não couber no espaço restante
        if y_inicial + altura_total > pdf.page_break_trigger:
            pdf.add_page()
            y_inicial = pdf.get_y()

        x = x_inicial
        for largura, linhas, alinhamento in zip(larguras, linhas_colunas, alinhamentos):
            pdf.rect(
                x, y_inicial, largura, altura_total, style="FD" if preenchido else ""
            )
            for i, linha in enumerate(linhas):
                pdf.set_xy(x, y_inicial + i * altura_linha)
                pdf.cell(largura, altura_linha, linha, border=0, align=alinhamento)
            x += largura

        pdf.set_xy(x_inicial, y_inicial + altura_total)

    def texto_multilinha(texto, altura_linha=4.5):
        """
        Substitui multi_cell() nativo pra parágrafos de texto livre (fora de
        tabela). O multi_cell do fpdf2 estava lançando FPDFException ("Not
        enough horizontal space...") em produção nessa versão/ambiente -
        usar a mesma técnica manual e estável da tabela evita depender
        daquele código interno.
        """
        largura_disponivel = pdf.w - pdf.l_margin - pdf.r_margin
        linhas = quebrar_texto(texto, largura_disponivel)
        for linha in linhas:
            if pdf.get_y() + altura_linha > pdf.page_break_trigger:
                pdf.add_page()
            pdf.set_x(pdf.l_margin)
            pdf.cell(largura_disponivel, altura_linha, linha, border=0, align="L")
            pdf.ln(altura_linha)

    # =====================================================================
    # Cabeçalho — tema preto/cinza, sem laranja
    # =====================================================================
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 10, p("PRONTUÁRIO GERONTOLÓGICO"), 0, 1, "C")

    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(
        0, 5, p("Sistema de Monitoramento e Avaliação Multidimensional"), 0, 1, "C"
    )
    pdf.ln(3)

    pdf.set_draw_color(20, 20, 20)
    pdf.set_line_width(0.6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # Identificação do Profissional
    nome_p = (
        str(dados_prof.get("nome", "PROFISSIONAL")).upper()
        if dados_prof
        else "PROFISSIONAL"
    )
    cargo_p = (
        str(dados_prof.get("profissao", "ESPECIALISTA")).upper()
        if dados_prof
        else "ESPECIALISTA"
    )
    reg_p = str(dados_prof.get("registro", "N/A")).upper() if dados_prof else "N/A"
    cidade_p = str(dados_prof.get("cidade", "LOCAL")).upper() if dados_prof else "LOCAL"
    data_emissao = datetime.date.today().strftime("%d/%m/%Y")

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(120, 6, p(f"Avaliador: {nome_p} ({cargo_p} - {reg_p})"), 0, 0, "L")
    pdf.cell(70, 6, p(f"Data: {data_emissao} | {cidade_p}"), 0, 1, "R")
    pdf.ln(5)

    # =====================================================================
    # 1. Identificação do Paciente
    # =====================================================================
    pdf.set_fill_color(30, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, p("  1. IDENTIFICAÇÃO DO PACIENTE"), 0, 1, "L", True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(95, 6, p(f"Nome: {nome_paciente}"), 0, 0)
    pdf.cell(45, 6, p(f"Idade: {idade_paciente} anos"), 0, 0)
    pdf.cell(50, 6, p(f"Sexo: {sexo_paciente}"), 0, 1)
    pdf.ln(5)

    # =====================================================================
    # 2. Histórico de Protocolos e Avaliações
    # =====================================================================
    pdf.set_fill_color(30, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, p("  2. HISTÓRICO DE PROTOCOLOS E AVALIAÇÕES"), 0, 1, "L", True)
    pdf.ln(2)

    larguras_colunas = (25, 55, 20, 90)
    alinhamentos_colunas = ["C", "L", "C", "L"]

    pdf.set_draw_color(190, 190, 190)  # bordas da tabela em cinza claro

    # Cabeçalho da tabela
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(60, 60, 60)
    pdf.set_text_color(255, 255, 255)
    celula_tabela(
        larguras_colunas,
        [p("Data"), p("Protocolo"), p("Pontos"), p("Resultado")],
        altura_linha=6,
        alinhamentos=alinhamentos_colunas,
        preenchido=True,
    )

    # Linhas da tabela (com zebra striping pra facilitar leitura)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(20, 20, 20)
    linha_par = False
    for _, inline in df_filtrado.iterrows():
        try:
            det = (
                ast.literal_eval(inline["detalhes"])
                if isinstance(inline["detalhes"], str)
                else inline["detalhes"]
            )
            pdf.set_fill_color(240, 240, 240) if linha_par else pdf.set_fill_color(
                255, 255, 255
            )
            celula_tabela(
                larguras_colunas,
                [
                    p(str(inline["data"])),
                    p(inline["tipo"].split("(")[0].strip()),
                    p(str(det.get("pontuacao", "N/A"))),
                    p(str(det.get("resultado", "---"))),
                ],
                altura_linha=5,
                alinhamentos=alinhamentos_colunas,
                preenchido=True,
            )
            linha_par = not linha_par
        except Exception:
            pass

    # =====================================================================
    # 3. Referência Técnica — Comparação com a Literatura
    # =====================================================================
    # Pra cada protocolo que apareceu no histórico do paciente, mostra o
    # ponto de corte estabelecido pela literatura e a citação, lado a lado
    # com o resultado já visto na tabela acima - ajuda o profissional a
    # embasar a conduta sem precisar consultar outra fonte na hora.
    protocolos_no_historico = []
    for _, inline in df_filtrado.iterrows():
        nome_base = inline["tipo"].split("(")[0].strip()
        if nome_base not in protocolos_no_historico:
            protocolos_no_historico.append(nome_base)

    referencias_aplicaveis = [
        (nome, REFERENCIAS_LITERATURA[nome])
        for nome in protocolos_no_historico
        if nome in REFERENCIAS_LITERATURA
    ]

    if referencias_aplicaveis:
        pdf.ln(6)
        pdf.set_fill_color(30, 30, 30)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(
            0,
            7,
            p("  3. REFERÊNCIA TÉCNICA - COMPARAÇÃO COM A LITERATURA"),
            0,
            1,
            "L",
            True,
        )
        pdf.ln(2)

        for nome, ref in referencias_aplicaveis:
            if pdf.get_y() > pdf.page_break_trigger - 20:
                pdf.add_page()

            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(31, 75, 68)
            pdf.cell(0, 5, p(nome), 0, 1, "L")

            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(20, 20, 20)
            texto_multilinha(p(ref["corte"]))

            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(110, 110, 110)
            texto_multilinha(p(f"Fonte: {ref['citacao']}"))
            pdf.ln(2)

    # =====================================================================
    # 4. Parecer Técnico e Conduta
    # =====================================================================
    pdf.ln(4)
    pdf.set_fill_color(30, 30, 30)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, p("  4. PARECER TÉCNICO E CONDUTA"), 0, 1, "L", True)
    pdf.ln(2)

    ev_texto = dados_paciente.get("evolucao_clinica", "").strip()
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(20, 20, 20)
    texto_multilinha(
        p(ev_texto if ev_texto else "Sem parecer registrado."), altura_linha=5
    )

    # Aviso de responsabilidade — os pontos de corte são referência geral da
    # literatura, não substituem o julgamento clínico do profissional.
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(140, 140, 140)
    texto_multilinha(
        p(
            "Os pontos de corte da seção 3 são referências gerais da literatura "
            "científica e não substituem o julgamento clínico individualizado do "
            "profissional responsável pela avaliação."
        ),
        altura_linha=4,
    )

    # Rodapé com numeração de página
    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(140, 140, 140)
    pdf.cell(
        0,
        10,
        p(f"Gerado por GerontoData em {data_emissao} - Página {pdf.page_no()}"),
        0,
        0,
        "C",
    )

    pdf_output = pdf.output()

    # CORREÇÃO:
    # fpdf2 retorna um bytearray (não é 'bytes' nem tem '.encode'). O código
    # antigo não reconhecia bytearray, caía no "else" e fazia str(bytearray),
    # transformando o PDF binário em texto - isso corrompia o arquivo e dava
    # "Falha ao carregar documento PDF" no navegador. Agora tratamos bytearray
    # e bytes da mesma forma (convertendo para bytes puro).
    if isinstance(pdf_output, (bytes, bytearray)):
        return bytes(pdf_output)
    elif hasattr(pdf_output, "encode"):
        return pdf_output.encode("latin-1")
    else:
        # Fallback de segurança caso retorne algo inesperado
        return bytes(pdf_output)


# =====================================================================
# INTERFACE DE AUTENTICAÇÃO
# =====================================================================
if "id_profissional" not in st.session_state:
    st.session_state.id_profissional = None
    st.session_state.usuario_logado = None
    st.session_state.token_sessao = None

if st.session_state.id_profissional is None:
    st.markdown(
        """
        <div style='text-align:center; padding: 34px 20px 26px 20px;
                    background: linear-gradient(135deg, #E6EFE9 0%, #F2F6F3 55%, #E9F1EC 100%);
                    border-radius: 20px; margin: 24px auto 26px auto; max-width: 540px;
                    box-shadow: 0 6px 24px rgba(31, 75, 68, 0.10);'>
            <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" width="56" height="56" style="margin-bottom: 10px;">
                <defs>
                    <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#1F4B44"/>
                        <stop offset="100%" stop-color="#4C7A6D"/>
                    </linearGradient>
                </defs>
                <circle cx="32" cy="32" r="30" fill="url(#logoGrad)"/>
                <path d="M32 45c-8.5-6.2-15-11.6-15-19a9.5 9.5 0 0 1 17-5.8A9.5 9.5 0 0 1 51 26c0 7.4-6.5 12.8-15 19z" fill="#FFFFFF" opacity="0.96"/>
            </svg>
            <h1 style='color: #1F4B44; font-family: "Source Serif 4", Georgia, serif; font-size: 34px; margin: 4px 0 2px 0; font-weight: 700;'>
                GerontoData
            </h1>
            <p style='color: #5B6B64; font-family: "IBM Plex Sans", sans-serif; font-weight: 600; font-size: 14px; letter-spacing: 0.03em; text-transform: uppercase; margin: 0;'>
                Beta 1.0 · Portal de Avaliação Multidisciplinar do Idoso
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, col_central, _ = st.columns([1, 2, 1])
    with col_central:
        aba_login, aba_cad, aba_esqueci = st.tabs(
            ["🔒 Acessar Portal", "📝 Cadastro do Profissional", "🔑 Recuperar Acesso"]
        )

        with aba_login:
            with st.form("login_whitebook"):
                u = st.text_input("E-mail Cadastrado:")
                s = st.text_input("Senha:", type="password")
                if st.form_submit_button("Entrar no Painel"):
                    dados = banco.verificar_login(u, s)
                    if dados:
                        id_prof, nome_prof, email_prof = dados[0], dados[1], dados[2]
                        token = str(random.randint(100000, 999999))

                        conn = banco.conectar_banco()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE profissionais SET sessao_ativa = ? WHERE id_profissional = ?",
                            (token, id_prof),
                        )
                        conn.commit()
                        conn.close()

                        st.session_state.id_profissional = id_prof
                        st.session_state.usuario_logado = nome_prof
                        st.session_state.token_sessao = token
                        st.rerun()
                    else:
                        st.error("E-mail ou senha incorretos.")

        with aba_cad:
            with st.form("cad_profissional_completo"):
                st.markdown("##### 🩺 Ficha de Identificação do Profissional")
                nome_p = st.text_input("Nome Completo (Sem abreviações):")
                email_p = st.text_input("E-mail Institucional:")
                senha_p = st.text_input("Definir Senha de Acesso:", type="password")

                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    # 🌟 PADRONIZADO: Campo de data limpo com máscara/dica visual padrão brasileira
                    dt_nasc_p = st.text_input("Data de Nascimento:", value="00/00/0000")
                    tel_p = st.text_input("Telefone de Contato:")
                with col_c2:
                    cidade_p = st.text_input("Cidade de Atuação:")
                    end_p = st.text_input("Endereço Comercial:")

                st.markdown("##### 📜 Registro de Classe de Saúde")
                profissao_p = st.selectbox(
                    "Sua Área de Atuação:",
                    [
                        "Gerontólogo",
                        "Fisioterapeuta",
                        "Médico",
                        "Enfermeiro",
                        "Terapeuta Ocupacional",
                        "Psicólogo",
                        "Nutricionista",
                        "Fonoaudiólogo",
                        "Outro",
                    ],
                )
                registro_p = st.text_input(
                    "Registro do Conselho Profissional (Ex: CBO Gerontologia, CREFITO 1234-F, CRM 5678):"
                )

                if st.form_submit_button("Concluir Credenciamento"):
                    if not nome_p or not email_p or not senha_p or not registro_p:
                        st.error("Campos obrigatórios ausentes!")
                    elif "@" not in email_p:
                        st.error("E-mail inválido!")
                    else:
                        if banco.cadastrar_usuario_completo(
                            nome_p,
                            email_p,
                            senha_p,
                            dt_nasc_p,
                            cidade_p,
                            tel_p,
                            end_p,
                            profissao_p,
                            registro_p,
                        ):
                            st.success(
                                "Cadastro realizado com sucesso! Vá para a aba de login."
                            )
                        else:
                            st.error("E-mail já cadastrado no sistema.")

        with aba_esqueci:
            with st.form("form_rec"):
                em = st.text_input("E-mail cadastrado:")
                if st.form_submit_button("Pedir Token"):
                    st.info("Simulado. Código padrão: 123456")
            with st.form("form_reset"):
                em_c = st.text_input("E-mail:")
                tk_c = st.text_input("Código:")
                ns_c = st.text_input("Nova Senha:", type="password")
                if st.form_submit_button("Alterar"):
                    if tk_c == "123456":
                        conn = banco.conectar_banco()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE profissionais SET senha = ? WHERE usuario = ?",
                            (ns_c, em_c),
                        )
                        conn.commit()
                        conn.close()
                        st.success("Senha alterada!")
    st.stop()

# Checagem de login único por pessoa ativo
id_prof = st.session_state.id_profissional
conn = banco.conectar_banco()
cursor = conn.cursor()
cursor.execute(
    "SELECT sessao_ativa, nome, profissao, registro_conselho, cidade, cargo FROM profissionais WHERE id_profissional = ?",
    (id_prof,),
)
ficha_prof_banco = cursor.fetchone()
conn.close()

if ficha_prof_banco and ficha_prof_banco[0] != st.session_state.token_sessao:
    st.warning("⚠️ Conta acessada em outro dispositivo.")
    st.session_state.id_profissional = None
    st.stop()

# Garante que o profissional tenha uma clinica_id vinculada -> sem isso o
# webhook do n8n nunca é encontrado (fica sempre em silêncio, sem erro visível).
clinica_id_prof = banco.garantir_clinica_do_profissional(id_prof)

dados_prof_logado = {
    "nome": ficha_prof_banco[1],
    "profissao": ficha_prof_banco[2],
    "registro": ficha_prof_banco[3],
    "cidade": ficha_prof_banco[4],
    "cargo": ficha_prof_banco[5],
}

# =====================================================================
# PAINEL LOGADO PRINCIPAL
# =====================================================================
col_user, col_logout = st.columns([4, 1])
col_user.markdown(
    f"👨‍⚕️ <span style='color: #1A202C !important; font-weight: bold;'>Especialista: Dr(a). {st.session_state.usuario_logado} ({dados_prof_logado['profissao']})</span>",
    unsafe_allow_html=True,
)

if col_logout.button("Sair", type="secondary"):
    st.session_state.id_profissional = None
    st.rerun()

# --- Configurações da Conta ---
with st.expander("⚙️ Configurações da Conta"):
    st.warning("⚠️ Esta ação é irreversível. Todos os seus dados serão apagados.")

    # Checkbox para confirmar a intenção do usuário
    confirmacao = st.checkbox(
        "Estou ciente de que perderei todos os prontuários e dados cadastrados."
    )

    # O botão de exclusão só é exibido se o checkbox estiver marcado
    if confirmacao:
        if st.button("Confirmar Exclusão Definitiva", type="primary"):
            banco.deletar_profissional(st.session_state.id_profissional)
            st.session_state.id_profissional = None
            st.success("Conta excluída com sucesso.")
            st.rerun()

# Lista de abas atualizada
menu_principal = st.tabs(
    [
        "⚡ Aplicar Escala",
        "📊 Evolução & Prontuários",
        "📝 Novo Idoso",
        "📬 Contato & Feedback",
        "🔗 Integrações",
    ]
)


# NOTA: aqui existia um segundo caminho de disparo do n8n (obter_webhook_url +
# disparar_webhook_n8n + callback_disparo), mas o callback_disparo nunca era
# chamado de verdade - só uma linha comentada. Código morto, removido. O
# disparo real do n8n (opcional) e o compartilhamento via WhatsApp (padrão,
# sem configuração) já acontecem dentro de escalas.salvar_avaliacao().


# --- ABA 1: APLICAR ESCALA ---
with menu_principal[0]:
    st.markdown("### ⚡ Aplicar Escala Gerontológica")
    conn = banco.conectar_banco()
    df_pacientes = pd.read_sql_query(
        "SELECT id_paciente, nome FROM pacientes WHERE id_profissional = ?",
        conn,
        params=(id_prof,),
    )
    conn.close()

    if df_pacientes.empty:
        st.warning("Cadastre o seu primeiro idoso.")
    else:
        dic_p = dict(zip(df_pacientes["nome"], df_pacientes["id_paciente"]))
        p_sel = st.selectbox("Selecione o Idoso de hoje:", list(dic_p.keys()))
        id_p = dic_p[p_sel]

        teste = st.selectbox(
            "Selecione o Protocolo:",
            [
                "Triagem Inicial (Sinais Vitais e Clínicos)",
                "💊 Rotina de Medicamentos Diários",
                "MEEM (Cognição)",
                "TDR (Desenho do Relógio)",
                "TUG (Mobilidade e Quedas)",
                "Katz (ABVD - Autocuidado)",
                "Lawton (AIVD - Funcionalidade)",
                "GDS-15 (Humor/Depressão)",
                "Zarit-22 (Sobrecarga de Cuidador)",
                "DUREL (Religiosidade de Duke)",
            ],
        )
        st.divider()

        if "Triagem" in teste:
            escalas.triagem_inicial_local(id_p, id_prof)

        elif "Medicamentos" in teste or "💊" in teste:
            escalas.gestao_medicamentos_local(id_p, id_prof)

        elif "MEEM" in teste:
            # Você pode passar o callback para o seu módulo scales para ele acionar ao clicar no botão 'Salvar' lá dentro!
            # Caso a sua função nativa de escala ainda não suporte callbacks, você pode implementá-lo no 'escalas.py'
            escalas.mini_mental_local(id_p, id_prof)

        elif "TDR" in teste:
            escalas.teste_relogio_local(id_p, id_prof)

        elif "TUG" in teste:
            escalas.teste_tug_local(id_p, id_prof)

        elif "Katz" in teste:
            escalas.escala_katz_local(id_p, id_prof)

        elif "Lawton" in teste:
            escalas.escala_lawton_local(id_p, id_prof)

        elif "GDS-15" in teste:
            escalas.escala_gds_local(id_p, id_prof)

        elif "Zarit-22" in teste:
            escalas.escala_zarit_local(id_p, id_prof)

        elif "DUREL" in teste:
            escalas.renderizar_escala_durel(id_p)

# --- ABA 2: DASHBOARD ---
with menu_principal[1]:
    st.markdown("### 📊 Evolução e Central de Prontuários")
    conn = banco.conectar_banco()
    df_pacientes = pd.read_sql_query(
        "SELECT id_paciente, nome, idade, sexo FROM pacientes WHERE id_profissional = ?",
        conn,
        params=(id_prof,),
    )
    conn.close()

    if df_pacientes.empty:
        st.warning("Nenhum prontuário ativo.")
    else:
        dic_p = dict(zip(df_pacientes["nome"], df_pacientes["id_paciente"]))
        p_sel = st.selectbox("Selecione o Idoso para Análise:", list(dic_p.keys()))
        id_p = dic_p[p_sel]

        idade_p = df_pacientes.loc[df_pacientes["id_paciente"] == id_p, "idade"].values[
            0
        ]
        sexo_p = df_pacientes.loc[df_pacientes["id_paciente"] == id_p, "sexo"].values[0]

        conn = banco.conectar_banco()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT endereco, contato_emergencia, tratamentos, evolucao_clinica, whatsapp_responsavel FROM pacientes WHERE id_paciente = ?",
                (id_p,),
            )
            dados_banco = cursor.fetchone()
        except sqlite3.OperationalError:
            # Coluna nova ainda não disponível nesse banco por algum motivo -
            # segue sem quebrar o app, só sem o campo de WhatsApp por ora.
            cursor.execute(
                "SELECT endereco, contato_emergencia, tratamentos, evolucao_clinica FROM pacientes WHERE id_paciente = ?",
                (id_p,),
            )
            linha_sem_whats = cursor.fetchone()
            dados_banco = (*linha_sem_whats, None) if linha_sem_whats else None
        conn.close()

        dados_paciente = {}
        evolucao_salva = ""
        whatsapp_salvo = ""
        if dados_banco:
            dados_paciente = {
                "endereco": dados_banco[0],
                "contato_emergencia": dados_banco[1],
                "tratamentos": dados_banco[2],
            }
            evolucao_salva = dados_banco[3] if dados_banco[3] else ""
            whatsapp_salvo = dados_banco[4] if dados_banco[4] else ""

        conn = banco.conectar_banco()
        df_filtrado = pd.read_sql_query(
            "SELECT rowid AS id_avaliacao, tipo, data, detalhes FROM avaliacoes WHERE id_paciente = ? ORDER BY data DESC",
            conn,
            params=(id_p,),
        )
        conn.close()

        if df_filtrado.empty:
            st.info("Sem testes gravados.")
        else:
            st.markdown("#### 🗒️ Resumo Clínico de Escalas")
            for _, inline in df_filtrado.iterrows():
                id_avaliacao = inline["id_avaliacao"]
                tipo = inline["tipo"]
                data = inline["data"]
                try:
                    det = (
                        ast.literal_eval(inline["detalhes"])
                        if isinstance(inline["detalhes"], str)
                        else inline["detalhes"]
                    )
                except:
                    det = {}
                dt_ex = (
                    f"{data.split('-')[2]}/{data.split('-')[1]}/{data.split('-')[0]}"
                    if "-" in str(data)
                    else data
                )

                col_card, col_lixo = st.columns([5, 1])
                with col_card:
                    st.markdown(
                        f"""
                    <div class="medical-card">
                        <span style='color: #5B6B64 !important; font-size: 12px; font-weight: bold;'>⏱️ {dt_ex}</span>
                        <strong style='display:block; color: #1F4B44 !important; font-family: "Source Serif 4", Georgia, serif !important; font-size: 16px; margin-top: 2px;'>{tipo.split("(")[0]}</strong>
                        <p style='margin: 4px 0 0 0; font-size: 14px;'>Resultado: <span class="dado-clinico">{det.get("resultado", "Registrado")}</span></p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                with col_lixo:
                    if st.button("❌ Excluir", key=f"del_{id_avaliacao}"):
                        conn = banco.conectar_banco()
                        cursor = conn.cursor()
                        cursor.execute(
                            "DELETE FROM avaliacoes WHERE rowid = ?", (id_avaliacao,)
                        )
                        conn.commit()
                        conn.close()
                        st.success("Excluído!")
                        st.rerun()

            st.divider()
            st.markdown("#### 📲 WhatsApp para receber os resultados")
            novo_whatsapp = st.text_input(
                "Número com DDD (deixe em branco pra escolher o contato manualmente):",
                value=whatsapp_salvo,
                placeholder="Ex: 13981221334",
                key="whatsapp_responsavel_input",
            )
            if st.button("💾 Salvar número"):
                conn = banco.conectar_banco()
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "UPDATE pacientes SET whatsapp_responsavel = ? WHERE id_paciente = ?",
                        (novo_whatsapp.strip() if novo_whatsapp else None, id_p),
                    )
                    conn.commit()
                    conn.close()
                    st.success("Número salvo!")
                    st.rerun()
                except sqlite3.OperationalError:
                    # Última tentativa: cria a coluna na hora e tenta de novo
                    try:
                        cursor.execute(
                            "ALTER TABLE pacientes ADD COLUMN whatsapp_responsavel TEXT"
                        )
                        cursor.execute(
                            "UPDATE pacientes SET whatsapp_responsavel = ? WHERE id_paciente = ?",
                            (novo_whatsapp.strip() if novo_whatsapp else None, id_p),
                        )
                        conn.commit()
                        conn.close()
                        st.success("Número salvo!")
                        st.rerun()
                    except sqlite3.OperationalError as e:
                        conn.close()
                        st.error(f"Não foi possível salvar o número agora: {e}")

            st.divider()
            st.markdown("#### ✍️ Evolução e Parecer Clínico Unificado")
            texto_evolucao = st.text_area(
                "Notas médicas:",
                value=evolucao_salva,
                placeholder="Digite o parecer final...",
                key="evolucao_clinica_input",
            )

            if st.button("Gravar Diagnóstico"):
                banco.salvar_evolucao_paciente(id_p, texto_evolucao)
                st.success("Gravado!")
                st.rerun()

            st.divider()
            dados_paciente["evolucao_clinica"] = texto_evolucao
            pdf_bytes = gerar_pdf_historico(
                df_filtrado, p_sel, idade_p, sexo_p, dados_paciente, dados_prof_logado
            )

            st.download_button(
                label="🖨️ Emitir Prontuário Oficial (PDF)",
                data=pdf_bytes,
                file_name=f"Prontuario_{p_sel.replace(' ', '_')}.pdf",
                mime="application/pdf",
            )

# --- ABA 3: NOVO IDOSO ---
with menu_principal[2]:
    st.markdown("### 👤 Novo Registro de Idoso")
    with st.form("cadastro_paciente_whitebook", clear_on_submit=True):
        nome = st.text_input("Nome Completo:")

        col_i1, col_i2 = st.columns(2)
        with col_i1:
            id_cron = st.number_input(
                "Idade Cronológica:", min_value=0, max_value=120, value=70
            )
        with col_i2:
            sexo = st.selectbox("Sexo Biológico:", ["Masculino", "Feminino", "Outro"])

        endereco = st.text_input("Endereço Residencial:")

        # 🌟 NOVOS CAMPOS ADICIONADOS DIRETAMENTE NO FORMULÁRIO DO IDOSO
        contato_emergencia = st.text_input(
            "Contato de Emergência (Nome, Parentesco e Telefone):",
            placeholder="Ex: Kaio Cesar (Filho) - (13) 98122-1334",
        )
        tratamentos_ativos = st.text_input(
            "Tratamentos Clínicos Ativos:",
            placeholder="Ex: Nutricionista, Fisioterapia, Cardiologista",
        )
        whatsapp_responsavel = st.text_input(
            "WhatsApp para receber os resultados (com DDD):",
            placeholder="Ex: 13981221334",
            help="O botão 'Compartilhar no WhatsApp' de cada avaliação vai abrir "
            "direto na conversa com esse número. Deixe em branco se preferir "
            "escolher o contato manualmente toda vez.",
        )

        if st.form_submit_button("Salvar Registro Clínico") and nome:
            conn = banco.conectar_banco()
            cursor = conn.cursor()

            valores_paciente = (
                id_prof,
                nome,
                id_cron,
                sexo,
                endereco,
                contato_emergencia if contato_emergencia else "Não Informado",
                tratamentos_ativos if tratamentos_ativos else "Nenhum",
                whatsapp_responsavel.strip() if whatsapp_responsavel else None,
            )

            # 🌟 AGORA SALVANDO OS DADOS REAIS RECOLHIDOS NO FORMULÁRIO NATIVO
            try:
                cursor.execute(
                    """
                    INSERT INTO pacientes (id_profissional, nome, idade, sexo, endereco, contato_emergencia, tratamentos, whatsapp_responsavel) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    valores_paciente,
                )
            except sqlite3.OperationalError:
                # Última tentativa: cria a coluna na hora e tenta de novo
                cursor.execute(
                    "ALTER TABLE pacientes ADD COLUMN whatsapp_responsavel TEXT"
                )
                cursor.execute(
                    """
                    INSERT INTO pacientes (id_profissional, nome, idade, sexo, endereco, contato_emergencia, tratamentos, whatsapp_responsavel) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    valores_paciente,
                )
            conn.commit()
            conn.close()
            st.success("Idoso registrado com sucesso!")
            st.rerun()

# Conteúdo da nova aba (aba 4)
with menu_principal[3]:
    email_sessao = st.session_state.get("email", dados_prof_logado.get("nome", ""))
    renderizar_aba_feedback(email_sessao)

    # O painel com TODOS os feedbacks só aparece para quem é admin.
    if dados_prof_logado.get("cargo") == "admin":
        st.markdown("---")
        st.markdown("### 👑 Painel do Administrador - Feedbacks Recebidos")
        try:
            conn = banco.conectar_banco()
            df_feedbacks = pd.read_sql_query(
                "SELECT * FROM feedbacks ORDER BY id DESC", conn
            )
            conn.close()
            if not df_feedbacks.empty:
                st.dataframe(df_feedbacks, use_container_width=True)
            else:
                st.info("Nenhum feedback registrado até o momento.")
        except Exception as e:
            st.error(f"Erro ao carregar painel admin: {e}")

# --- ABA 5: INTEGRAÇÕES (N8N / WHATSAPP) ---
# Esta aba tinha sumido do menu quando o código de navegação antigo foi
# removido - sem ela não existia como colar/editar a URL do webhook do n8n.
with menu_principal[4]:
    renderizar_configuracoes_integracao(clinica_id_prof)


def verificar_acesso(nivel_requerido):
    """
    nivel_requerido: 'admin' ou 'profissional'
    Usa a ficha do profissional já carregada no login (dados_prof_logado).
    """
    if (
        "id_profissional" not in st.session_state
        or st.session_state.id_profissional is None
    ):
        st.error("Faça login primeiro.")
        st.stop()

    if nivel_requerido == "admin" and dados_prof_logado.get("cargo") != "admin":
        st.error("Acesso negado: Apenas administradores podem acessar esta área.")
        st.stop()
