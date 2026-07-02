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

# Configuração da identidade do App
st.set_page_config(
    page_title="GerontoData Beta 1.0",
    page_icon="https://raw.githubusercontent.com/uicai/storage/main/logo_geronto_clean.png",  # Link direto super leve!
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inicializa banco expandido
banco.criar_tabelas()

# =====================================================================
# 🎨 BLINDAGEM VISUAL AVANÇADA WHITEBOOK (CONTRASTE UNIVERSAL)
# =====================================================================
st.markdown(
    """
    <link rel="icon" href="https://raw.githubusercontent.com/uicai/storage/main/logo_geronto_clean.png" type="image/png">
    <link rel="apple-touch-icon" href="https://raw.githubusercontent.com/uicai/storage/main/logo_geronto_clean.png">
    <style>
        /* 1. EXTINÇÃO DA BARRA SUPERIOR E MENUS NATIVOS */
        [data-testid="stHeader"], header, .stActionButton, [data-testid="stDecoration"] {
            display: none !important;
        }
        
        /* 2. FORÇAR FUNDO BRANCO INTEGRAL NA TELA */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMainBlockContainer"], [data-testid="stForm"] {
            background-color: #FFFFFF !important;
            color: #1A202C !important;
        }
        
        p, span, label, li, th, td, div, small, [data-testid="stMarkdownContainer"] p {
            color: #1A202C !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            color: #E67E22 !important;
            font-weight: 700 !important;
        }
        
        /* 3. CAPTURA E LIMPEZA DE TODOS OS PONTOS ESCUROS DOS SELETORES (SELECTBOX) */
        div[data-baseweb="select"], 
        div[data-baseweb="select"] > div, 
        [data-testid="stSelectbox"] div, 
        [data-testid="stSelectbox"] aria-box,
        .stSelectbox > div {
            background-color: #F8F9FA !important;
            color: #1A202C !important;
        }
        
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div,
        [data-testid="stSelectbox"] p,
        .stSelectbox span,
        .stSelectbox div {
            color: #1A202C !important;
        }

        input, textarea, select, .stTextArea textarea, div[data-baseweb="base-input"] > input {
            background-color: #F8F9FA !important;
            color: #1A202C !important;
            border: 1px solid #CBD5E0 !important;
            border-radius: 6px !important;
        }
        
        /* 4. LIMPEZA DOS MENUS SUSPENSOS QUANDO CLICADOS (POPOVERS) */
        div[role="listbox"], 
        ul[role="listbox"], 
        li[role="option"], 
        [data-baseweb="menu"], 
        [data-baseweb="popover"],
        div[data-baseweb="popover"] * {
            background-color: #FFFFFF !important;
            color: #1A202C !important;
        }
        li[role="option"] div, li[role="option"] span {
            color: #1A202C !important;
            background-color: #FFFFFF !important;
        }
        li[role="option"]:hover, li[role="option"]:hover div {
            background-color: #F1F3F5 !important;
            color: #E67E22 !important;
        }

        div[data-testid="stNumberInput"] button {
            background-color: #E67E22 !important;
            color: #FFFFFF !important;
        }

        /* 5. ADAPTABILIDADE DOS BOTÕES */
        @media (min-width: 768px) {
            div.stButton > button, [data-testid="stFormSubmitButton"] button { width: auto !important; min-width: 200px !important; padding: 10px 24px !important; display: inline-block !important; }
        }
        @media (max-width: 767px) {
            div.stButton > button, [data-testid="stFormSubmitButton"] button { width: 100% !important; padding: 14px 20px !important; font-size: 16px !important; display: block !important; }
            button[data-baseweb="tab"] { padding: 10px 12px !important; font-size: 14px !important; }
        }
        
        button, [data-testid="stFormSubmitButton"] button {
            background-color: #E67E22 !important;
            color: #FFFFFF !important;
            border-radius: 6px !important;
            border: none !important;
            font-weight: 600 !important;
        }
        
        .medical-card {
            background-color: #F8F9FA !important;
            border-left: 5px solid #E67E22 !important;
            border-radius: 6px !important;
            padding: 14px !important;
            margin-bottom: 12px !important;
        }
        button[data-baseweb="tab"] { background-color: transparent !important; color: #4A5568 !important; font-size: 15px !important; font-weight: 600 !important; border: none !important; }
        button[aria-selected="true"] { color: #E67E22 !important; border-bottom: 3px solid #E67E22 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


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
    pdf.set_auto_page_break(auto=True, margin=15)

    def p(texto):
        # Garante que caracteres especiais funcionem no PDF
        return (
            str(texto)
            .replace("—", "-")
            .replace("•", "-")
            .encode("cp1252", "ignore")
            .decode("cp1252")
        )

    # Cabeçalho
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(230, 126, 34)
    pdf.cell(0, 10, p("PRONTUÁRIO GERONTOLÓGICO"), 0, 1, "C")

    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(127, 140, 141)
    pdf.cell(
        0, 5, p("Sistema de Monitoramento e Avaliação Multidimensional"), 0, 1, "C"
    )
    pdf.ln(5)

    pdf.set_draw_color(230, 126, 34)
    pdf.line(10, 32, 200, 32)
    pdf.ln(5)

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
    pdf.set_text_color(52, 73, 94)
    pdf.cell(120, 6, p(f"Avaliador: {nome_p} ({cargo_p} - {reg_p})"), 0, 0, "L")
    pdf.cell(70, 6, p(f"Data: {data_emissao} | {cidade_p}"), 0, 1, "R")
    pdf.ln(4)

    # Identificação do Paciente
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 6, p("1. IDENTIFICAÇÃO DO PACIENTE"), 0, 1, "L")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)

    pdf.cell(95, 6, p(f"Nome: {nome_paciente}"), 0, 0)
    pdf.cell(45, 6, p(f"Idade: {idade_paciente} anos"), 0, 0)
    pdf.cell(50, 6, p(f"Sexo: {sexo_paciente}"), 0, 1)
    pdf.ln(4)

    # Histórico de Protocolos
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 6, p("2. HISTÓRICO DE PROTOCOLOS E AVALIAÇÕES"), 0, 1, "L")
    pdf.ln(2)

    # Tabela
    pdf.set_fill_color(230, 126, 34)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(25, 8, p("Data"), 1, 0, "C", True)
    pdf.cell(70, 8, p("Protocolo"), 1, 0, "L", True)
    pdf.cell(20, 8, p("Pontos"), 1, 0, "C", True)
    pdf.cell(75, 8, p("Resultado"), 1, 1, "L", True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)

    for _, inline in df_filtrado.iterrows():
        try:
            det = (
                ast.literal_eval(inline["detalhes"])
                if isinstance(inline["detalhes"], str)
                else inline["detalhes"]
            )
            pdf.cell(25, 8, str(inline["data"]), 1, 0, "C")
            pdf.cell(70, 8, p(inline["tipo"].split("(")[0]), 1, 0, "L")
            pdf.cell(20, 8, str(det.get("pontuacao", "N/A")), 1, 0, "C")
            pdf.cell(75, 8, p(str(det.get("resultado", "---"))), 1, 1, "L")
        except:
            pass

    # Parecer Técnico
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(230, 126, 34)
    pdf.cell(0, 6, p("3. PARECER TÉCNICO E CONDUTA"), 0, 1, "L")
    pdf.ln(2)
    ev_texto = dados_paciente.get("evolucao_clinica", "").strip()
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 5, p(ev_texto))

    pdf_output = pdf.output()

    # CORREÇÃO:
    # Se for bytes, retorna direto.
    # Se for string (ou algo que tenha .encode), codifica.
    if isinstance(pdf_output, bytes):
        return pdf_output
    elif hasattr(pdf_output, "encode"):
        return pdf_output.encode("latin-1")
    else:
        # Fallback de segurança caso retorne algo inesperado
        return str(pdf_output).encode("latin-1")


# =====================================================================
# INTERFACE DE AUTENTICAÇÃO
# =====================================================================
if "id_profissional" not in st.session_state:
    st.session_state.id_profissional = None
    st.session_state.usuario_logado = None
    st.session_state.token_sessao = None

if st.session_state.id_profissional is None:
    st.markdown(
        "<h1 style='text-align: center; color: #E67E22 !important; font-size: 36px; margin-top: 40px;'>🌱 GerontoData Beta1.0</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; font-weight: bold; margin-bottom: 30px;'>Portal de Avaliação Multidisciplinar do Idoso</p>",
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
    "SELECT sessao_ativa, nome, profissao, registro_conselho, cidade FROM profissionais WHERE id_profissional = ?",
    (id_prof,),
)
ficha_prof_banco = cursor.fetchone()
conn.close()

if ficha_prof_banco and ficha_prof_banco[0] != st.session_state.token_sessao:
    st.warning("⚠️ Conta acessada em outro dispositivo.")
    st.session_state.id_profissional = None
    st.stop()

dados_prof_logado = {
    "nome": ficha_prof_banco[1],
    "profissao": ficha_prof_banco[2],
    "registro": ficha_prof_banco[3],
    "cidade": ficha_prof_banco[4],
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
    ]
)
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
        cursor.execute(
            "SELECT endereco, contato_emergencia, tratamentos, evolucao_clinica FROM pacientes WHERE id_paciente = ?",
            (id_p,),
        )
        dados_banco = cursor.fetchone()
        conn.close()

        dados_paciente = {}
        evolucao_salva = ""
        if dados_banco:
            dados_paciente = {
                "endereco": dados_banco[0],
                "contato_emergencia": dados_banco[1],
                "tratamentos": dados_banco[2],
            }
            evolucao_salva = dados_banco[3] if dados_banco[3] else ""

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
                        <span style='color: #4A5568 !important; font-size: 12px; font-weight: bold;'>⏱️ {dt_ex}</span>
                        <strong style='display:block; color: #E67E22 !important; font-size: 16px; margin-top: 2px;'>{tipo.split("(")[0]}</strong>
                        <p style='margin: 4px 0 0 0; font-size: 14px;'>Resultado: {det.get("resultado", "Registrado")}</p>
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

        if st.form_submit_button("Salvar Registro Clínico") and nome:
            conn = banco.conectar_banco()
            cursor = conn.cursor()

            # 🌟 AGORA SALVANDO OS DADOS REAIS RECOLHIDOS NO FORMULÁRIO NATIVO
            cursor.execute(
                """
                INSERT INTO pacientes (id_profissional, nome, idade, sexo, endereco, contato_emergencia, tratamentos) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_prof,
                    nome,
                    id_cron,
                    sexo,
                    endereco,
                    contato_emergencia if contato_emergencia else "Não Informado",
                    tratamentos_ativos if tratamentos_ativos else "Nenhum",
                ),
            )
            conn.commit()
            conn.close()
            st.success("Idoso registrado com sucesso!")
            st.rerun()

# Conteúdo da nova aba (aba 4)
with menu_principal[3]:
    st.markdown("### 📬 Fale com o Desenvolvedor")
    st.write("Relate erros ou envie sugestões para melhorar o GerontoData.")

    with st.form("form_contato_v1"):
        assunto = st.selectbox(
            "Assunto:", ["Relato de Erro", "Sugestão de Melhoria", "Dúvida", "Outro"]
        )
        mensagem = st.text_area("Descreva aqui sua mensagem:")
        submit = st.form_submit_button("Enviar Feedback")

        if submit:
            # Por enquanto, vamos apenas salvar num arquivo ou exibir na tela
            # Depois, integraremos com o e-mail automático
            st.success("Obrigado pelo seu feedback! Ele foi registrado com sucesso.")
            # st.write(f"Enviado: {assunto} - {mensagem}") # Opcional: ver o que foi enviado


def renderizar_aba_feedback(usuario_email):
    st.markdown("### 📬 Central de Feedback & Suporte [Beta]")
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
            placeholder="Conte-nos o que aconteceu ou o que gostaria de ver no sistema...",
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


# =====================================================================
# 📬 MOTOR 1/4: SISTEMA DE FEEDBACK INTERNO [BETA 1.0]
# =====================================================================


def criar_tabela_feedback():
    """Garante que a tabela de feedbacks existe no banco SQLite"""
    try:
        conn = sqlite3.connect("gerontodata.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                tipo TEXT,
                mensagem TEXT,
                data TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao inicializar tabela de feedback: {e}")


def renderizar_aba_feedback(usuario_email):
    """Desenha a interface visual do formulário de feedback"""
    st.markdown("### 📬 Central de Feedback & Suporte [Beta]")
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


# Executa a criação da tabela logo na leitura do script
criar_tabela_feedback()

# =====================================================================
# 🧭 NAVEGAÇÃO DO SISTEMA ATUALIZADA
# =====================================================================

menu_opcoes = [
    "Painel Principal",
    "Meus Pacientes",
    "Realizar Escalas",
    "Central de Feedback",
]
escolha_menu = st.sidebar.selectbox("Navegação do Sistema", menu_opcoes)

if escolha_menu == "Painel Principal":
    st.write("Sua função do Dashboard / Painel Principal aqui")

elif escolha_menu == "Meus Pacientes":
    st.write("Sua função de listagem de pacientes aqui")

elif escolha_menu == "Realizar Escalas":
    st.write("Sua função que chama o arquivo escalas.py aqui")

# 3. ENCAIXE CIRÚRGICO DA NOVA TELA COM PAINEL ADM EMBUTIDO:
elif escolha_menu == "Central de Feedback":
    email_sessao = st.session_state.get("email", "usuario_beta@gerontodata.com")

    # 1. Desenha o formulário para o usuário enviar o feedback
    renderizar_aba_feedback(email_sessao)

    # 2. Se for você (Admin), renderiza as respostas recebidas logo abaixo na mesma página!
    # Altere essa linha para aceitar o e-mail padrão do teste também:
    # Mude a linha do 'if email_sessao == ...' para True:
if True:
    st.markdown("---")
    st.markdown("### 👑 Painel do Administrador - Feedbacks Recebidos")

    try:
        conn = sqlite3.connect("gerontodata.db")
        # Lê a tabela de feedbacks direto num DataFrame do Pandas
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

 def verificar_acesso(nivel_requerido):
    """
    nivel_requerido: 'admin' ou 'profissional'
    """
    if "usuario" not in st.session_state:
        st.error("Faça login primeiro.")
        st.stop()
    
    usuario = st.session_state["usuario"]
    if nivel_requerido == 'admin' and usuario['cargo'] != 'admin':
        st.error("Acesso negado: Apenas administradores podem acessar esta área.")
        st.stop()
