import streamlit as st
import sqlite3
import ast
import datetime
import urllib.parse
import requests  # Certifique-se de que importou o requests aqui!
from streamlit_drawable_canvas import st_canvas


def gerar_link_whatsapp(texto):
    """
    Gera um link 'wa.me' que abre o WhatsApp (app ou web) já com a mensagem
    pronta. Diferente do webhook do n8n, isso não exige nenhuma configuração
    externa - funciona pra qualquer profissional, na hora.
    """
    return "https://wa.me/?text=" + urllib.parse.quote(texto)


def disparar_webhook_n8n(tipo_teste, detalhes, id_paciente, id_profissional):
    """
    Busca a URL de webhook ativa para a clínica do profissional e dispara a automação.
    """
    try:
        conn = sqlite3.connect("gerontodata.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT clinica_id FROM profissionais WHERE id_profissional = ?",
            (id_profissional,),
        )
        res_prof = cursor.fetchone()

        if not res_prof or not res_prof[0]:
            conn.close()
            return False

        clinica_id = res_prof[0]

        cursor.execute(
            "SELECT url_webhook_n8n FROM integracoes_clinica WHERE clinica_id = ?",
            (clinica_id,),
        )
        res_url = cursor.fetchone()
        conn.close()

        if not res_url or not res_url[0]:
            return False

        n8n_url = res_url[0]

        payload = {
            "id_paciente": id_paciente,
            "id_profissional": id_profissional,
            "clinica_id": clinica_id,
            "tipo_teste": tipo_teste,
            "detalhes": detalhes,
        }

        resposta = requests.post(n8n_url, json=payload, timeout=3)
        return resposta.status_code == 200

    except Exception as e:
        print(f"⚠️ Erro silencioso ao disparar webhook para o n8n: {e}")
        return False


def salvar_avaliacao(id_paciente, id_profissional, tipo_teste, detalhes):
    try:
        if isinstance(detalhes, str):
            try:
                dict_detalhes = ast.literal_eval(detalhes)
            except Exception:
                dict_detalhes = {"dados_brutos": detalhes}
        else:
            dict_detalhes = detalhes if detalhes is not None else {}

        if "obs_clinica_atual" in st.session_state:
            dict_detalhes["observacao"] = st.session_state.get(
                "obs_clinica_atual", ""
            ).strip()

        detalhes_finais = str(dict_detalhes)

        conn = sqlite3.connect("gerontodata.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO avaliacoes (id_paciente, id_profissional, tipo, data, detalhes) VALUES (?, ?, ?, date('now'), ?)",
            (id_paciente, id_profissional, tipo_teste, detalhes_finais),
        )
        conn.commit()
        conn.close()

        # Integração avançada e OPCIONAL com n8n (só dispara se a clínica
        # tiver configurado uma URL de webhook na aba Integrações).
        disparar_webhook_n8n(tipo_teste, dict_detalhes, id_paciente, id_profissional)

        # Compartilhamento simples via WhatsApp - não exige nenhuma
        # configuração, funciona pra qualquer profissional na hora.
        resumo = dict_detalhes.get("resultado", "")
        pontos = dict_detalhes.get("pontuacao", "")
        texto_whats = (
            f"*GerontoData - {tipo_teste}*\nPontuação: {pontos}\nResultado: {resumo}"
        )
        st.link_button(
            "📲 Compartilhar resultado no WhatsApp",
            gerar_link_whatsapp(texto_whats),
            use_container_width=True,
        )

        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


def calcular_durel(p1, p2, p3, p4, p5):
    ro = p1
    rno = p2
    ri = p3 + p4 + p5
    analise = f"RO: {ro}/6 | RNO: {rno}/6 | RI: {ri}/15"
    return {"ro": ro, "rno": rno, "ri": ri, "analise": analise}


def renderizar_escala_durel(paciente_id):
    st.markdown("### 📑 Escala de Religiosidade de Duke (DUREL)")
    st.write("Avaliação do envolvimento religioso e espiritualidade.")

    with st.form("form_durel"):
        st.markdown("**1. Religiosidade Organizacional (RO)**")
        p1 = st.selectbox(
            "Frequência em igreja/templo:",
            [
                (6, "Mais de uma vez/semana"),
                (5, "Uma vez/semana"),
                (4, "Algumas vezes/mês"),
                (3, "Algumas vezes/ano"),
                (2, "Uma vez/ano ou menos"),
                (1, "Nunca"),
            ],
            format_func=lambda x: x[1],
        )[0]

        st.markdown("**2. Religiosidade Não-Organizacional (RNO)**")
        p2 = st.selectbox(
            "Atividades religiosas privadas (preces/meditação):",
            [
                (6, "Mais de uma vez/dia"),
                (5, "Diariamente"),
                (4, "2+ vezes/semana"),
                (3, "Uma vez/semana"),
                (2, "Poucas vezes/mês"),
                (1, "Raramente ou nunca"),
            ],
            format_func=lambda x: x[1],
        )[0]

        st.markdown("**3. Religiosidade Intrínseca (RI)**")
        p3 = st.selectbox(
            "Sinto presença do Divino:",
            [
                (5, "Totalmente de acordo"),
                (4, "Na maioria"),
                (3, "Não tenho certeza"),
                (2, "Grande parte discordo"),
                (1, "Totalmente discordo"),
            ],
        )[0]
        p4 = st.selectbox(
            "Crenças moldam a vida:",
            [
                (5, "Totalmente de acordo"),
                (4, "Na maioria"),
                (3, "Não tenho certeza"),
                (2, "Grande parte discordo"),
                (1, "Totalmente discordo"),
            ],
        )[0]
        p5 = st.selectbox(
            "Esforço para viver religião:",
            [
                (5, "Totalmente de acordo"),
                (4, "Na maioria"),
                (3, "Não tenho certeza"),
                (2, "Grande parte discordo"),
                (1, "Totalmente discordo"),
            ],
        )[0]

        botao = st.form_submit_button("Salvar")

        if botao:
            ri = p3 + p4 + p5
            resultado = f"DUREL - RO: {p1}/6 | RNO: {p2}/6 | RI: {ri}/15"
            try:
                conn = sqlite3.connect("gerontodata.db")
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO historico_escalas (paciente_id, escala_nome, resultado, data) VALUES (?, ?, ?, ?)",
                    (
                        paciente_id,
                        "DUREL",
                        resultado,
                        datetime.datetime.now().strftime("%d/%m/%Y"),
                    ),
                )
                conn.commit()
                conn.close()
                st.success("Salvo com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")


def mini_mental_local(id_paciente, id_profissional):
    st.markdown("### 🧠 Mini-Exame do Estado Mental (MEEM)")

    col1, col2 = st.columns(2)
    with col1:
        o_temporal = st.number_input(
            "Orientação Temporal (0-5):", min_value=0, max_value=5, value=5
        )
        registro = st.number_input(
            "Registro de 3 palavras (0-3):", min_value=0, max_value=3, value=3
        )
        evocacao = st.number_input(
            "Evocação / Memória (0-3):", min_value=0, max_value=3, value=3
        )
    with col2:
        o_espacial = st.number_input(
            "Orientação Espacial (0-5):", min_value=0, max_value=5, value=5
        )
        calculo = st.number_input(
            "Atenção e Cálculo (0-5):", min_value=0, max_value=5, value=5
        )
        linguagem = st.number_input(
            "Linguagem e Comandos (0-9):", min_value=0, max_value=9, value=9
        )

    escolaridade = st.selectbox(
        "Escolaridade do idoso:",
        [
            "Analfabeto",
            "1 a 4 anos de estudo",
            "5 a 8 anos de estudo",
            "9 a 11 anos de estudo",
            "Superior (Mais de 11 anos)",
        ],
    )
    cortes = {
        "Analfabeto": 20,
        "1 a 4 anos de estudo": 25,
        "5 a 8 anos de estudo": 26,
        "9 a 11 anos de estudo": 28,
        "Superior (Mais de 11 anos)": 29,
    }

    nota_corte = cortes[escolaridade]
    pontuacao = o_temporal + o_espacial + registro + calculo + evocacao + linguagem
    res = "Normal" if pontuacao >= nota_corte else "Alterado"

    st.metric(
        "Pontuação MEEM",
        f"{pontuacao} / 30",
        f"Corte para {escolaridade}: {nota_corte} ({res})",
    )

    if st.button("💾 Gravar Mini-Mental", type="primary", use_container_width=True):
        salvar_avaliacao(
            id_paciente,
            id_profissional,
            "Mini-Exame do Estado Mental (MEEM)",
            {
                "pontuacao": pontuacao,
                "resultado": res,
                "escolaridade": escolaridade,
            },
        )
        st.success("Registrado!")


def teste_relogio_local(id_paciente, id_profissional):
    st.markdown("### ⏰ Teste do Desenho do Relógio (TDR)")
    if "canvas_version" not in st.session_state:
        st.session_state.canvas_version = 0

    st_canvas(
        fill_color="rgba(255, 255, 255, 1)",
        stroke_width=4,
        stroke_color="#111827",
        background_color="#FFFFFF",
        height=250,
        width=250,
        drawing_mode="freedraw",
        key=f"tdr_{st.session_state.canvas_version}",
    )
    if st.button("🧼 Limpar"):
        st.session_state.canvas_version += 1
        st.rerun()

    c_numeros = st.checkbox("Círculo e números corretos (2 pts)")
    p_ponteiros = st.checkbox("Ponteiros na hora exata (2 pts)")
    pontuacao = (2 if c_numeros else 0) + (2 if p_ponteiros else 0)
    res = "Normal" if pontuacao == 4 else "Alterado"

    if st.button(
        "💾 Gravar Teste do Relógio", type="primary", use_container_width=True
    ):
        salvar_avaliacao(
            id_paciente,
            id_profissional,
            "Teste do Desenho do Relógio (TDR)",
            {"pontuacao": pontuacao, "resultado": res},
        )
        st.success("Salvo!")


def teste_tug_local(id_paciente, id_profissional):
    st.markdown("### 🏃 Teste Timed Up and Go (TUG)")
    tempo = st.number_input(
        "Tempo gasto (segundos):", min_value=0.0, value=10.0, step=0.1
    )
    risco = (
        "Baixo risco de quedas"
        if tempo < 10
        else ("Risco moderado" if tempo <= 20 else "Alto risco de quedas")
    )
    st.info(f"Classificação: {risco}")
    if st.button("💾 Salvar Teste TUG", type="primary", use_container_width=True):
        salvar_avaliacao(
            id_paciente,
            id_profissional,
            "Timed Up and Go (TUG)",
            {"pontuacao": tempo, "resultado": risco},
        )
        st.success("Salvo!")


def escala_katz_local(id_paciente, id_profissional):
    st.markdown("### 🛁 Índice de Katz (ABVD)")
    indep = sum(
        [
            st.checkbox("Banho"),
            st.checkbox("Vestir-se"),
            st.checkbox("Higiene Pessoal"),
            st.checkbox("Transferência"),
            st.checkbox("Continência"),
            st.checkbox("Alimentação"),
        ]
    )
    res = (
        "Independente"
        if indep == 6
        else ("Dependência Moderada" if indep >= 3 else "Dependência Grave")
    )
    st.metric("Atividades Independentes", f"{indep} / 6", res)
    if st.button("💾 Salvar Índice de Katz", type="primary", use_container_width=True):
        salvar_avaliacao(
            id_paciente,
            id_profissional,
            "Índice de Katz (ABVD)",
            {"pontuacao": indep, "resultado": res},
        )
        st.success("Salvo!")


def escala_lawton_local(id_paciente, id_profissional):
    st.markdown("### 📞 Escala de Lawton e Brody (AIVD)")
    t1 = st.slider("Telefone", 1, 3, 3)
    t2 = st.slider("Transporte", 1, 3, 3)
    t3 = st.slider("Compras", 1, 3, 3)
    t4 = st.slider("Refeições", 1, 3, 3)
    t5 = st.slider("Arrumar a casa", 1, 3, 3)
    t6 = st.slider("Roupas", 1, 3, 3)
    t7 = st.slider("Remédios", 1, 3, 3)
    t8 = st.slider("Finanças", 1, 3, 3)
    total = t1 + t2 + t3 + t4 + t5 + t6 + t7 + t8
    res = (
        "Independência total"
        if total == 24
        else ("Dependência parcial" if total >= 9 else "Dependência grave")
    )
    st.metric("Pontuação Total", f"{total} / 24", res)
    if st.button(
        "💾 Salvar Escala de Lawton", type="primary", use_container_width=True
    ):
        salvar_avaliacao(
            id_paciente,
            id_profissional,
            "Escala de Lawton e Brody (AIVD)",
            {"pontuacao": total, "resultado": res},
        )
        st.success("Salvo!")


def escala_gds_local(id_paciente, id_profissional):
    st.markdown("### 📉 Escala de Depressão Geriátrica (GDS-15)")
    perguntas = [
        "1. Satisfeito com a vida? (Marcar se NÃO)",
        "2. Interrompeu atividades? (Marcar se SIM)",
        "3. Vida vazia? (Marcar se SIM)",
        "4. Aborrece-se frequentemente? (Marcar se SIM)",
        "5. Bom humor sempre? (Marcar se NÃO)",
        "6. Medo que algo ruim aconteça? (Marcar se SIM)",
        "7. Feliz sempre? (Marcar se NÃO)",
        "8. Desamparado com frequência? (Marcar se SIM)",
        "9. Prefere ficar em casa? (Marcar se SIM)",
        "10. Mais problemas de memória? (Marcar se SIM)",
        "11. Maravilhoso estar vivo? (Marcar se NÃO)",
        "12. Inútil atualmente? (Marcar se SIM)",
        "13. Cheio de energia? (Marcar se NÃO)",
        "14. Situação sem esperança? (Marcar se SIM)",
        "15. Outros estão melhores? (Marcar se SIM)",
    ]
    pontos = sum([st.checkbox(p) for p in perguntas])
    res = (
        "Sem sintomas"
        if pontos <= 5
        else ("Sintomas leves" if pontos <= 10 else "Sintomas graves")
    )
    st.metric("Score GDS", f"{pontos} / 15", res)
    if st.button("💾 Salvar GDS-15", type="primary", use_container_width=True):
        salvar_avaliacao(
            id_paciente,
            id_profissional,
            "Escala de Depressao Geriatrica (GDS-15)",
            {"pontuacao": pontos, "resultado": res},
        )
        st.success("Salvo!")


def escala_zarit_local(id_paciente, id_profissional):
    st.markdown("### 👥 Escala de Sobrecarga do Cuidador (Zarit-22)")
    z1 = st.slider("O idoso pede mais ajuda do que precisa?", 0, 4, 0)
    z2 = st.slider("Falta tempo para si por causa do idoso?", 0, 4, 0)
    z3 = st.slider("Sente estresse entre cuidar e outras tarefas?", 0, 4, 0)
    total = int(min((z1 + z2 + z3) * 7.3, 88))
    res = (
        "Sobrecarga leve"
        if total <= 20
        else ("Sobrecarga moderada" if total <= 40 else "Sobrecarga grave")
    )
    st.metric("Sobrecarga Estimada", f"{total} / 88", res)
    if st.button("💾 Salvar Zarit-22", type="primary", use_container_width=True):
        salvar_avaliacao(
            id_paciente,
            id_profissional,
            "Escala Zarit-22 (Sobrecarga)",
            {"pontuacao": total, "resultado": res},
        )
        st.success("Salvo!")


def triagem_inicial_local(id_paciente, id_profissional):
    st.markdown("### 🩺 Triagem Inicial (Sinais Vitais e Clínicos)")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Sinais Vitais**")
        pa_sistolica = st.number_input(
            "Pressão Arterial Sistólica (Máxima - mmHg):",
            min_value=0,
            max_value=300,
            value=120,
        )
        pa_diastolica = st.number_input(
            "Pressão Arterial Diastólica (Mínima - mmHg):",
            min_value=0,
            max_value=200,
            value=80,
        )
        freq_cardiaca = st.number_input(
            "Frequência Cardíaca (BPM):",
            min_value=0,
            max_value=250,
            value=70,
        )

        st.markdown("**Antropometria**")
        peso = st.number_input(
            "Peso (kg):",
            min_value=0.0,
            max_value=250.0,
            value=70.0,
            step=0.1,
        )
        altura = st.number_input(
            "Altura (metros):",
            min_value=0.0,
            max_value=2.50,
            value=1.65,
            step=0.01,
        )
        panturrilha = st.number_input(
            "Circunferência da Panturrilha (cm):",
            min_value=0.0,
            max_value=100.0,
            value=34.0,
            step=0.1,
        )

    with col2:
        st.markdown("**Histórico de Comorbidades / Doenças**")
        doencas = []
        if st.checkbox("Hipertensão Arterial (HAS)"):
            doencas.append("HAS")
        if st.checkbox("Diabetes Mellitus (DM)"):
            doencas.append("DM")
        if st.checkbox("Dislipidemia (Colesterol Alto)"):
            doencas.append("Dislipidemia")
        if st.checkbox("Cardiopatia / Problemas no Coração"):
            doencas.append("Cardiopatia")
        if st.checkbox("Histórico de AVC / Derrame"):
            doencas.append("Histórico de AVC")
        if st.checkbox("Artrose / Osteoporose"):
            doencas.append("Osteoarticular")
        if st.checkbox("Depressão / Ansiedade"):
            doencas.append("Saúde Mental")

        outras_doencas = st.text_input("Outras condições (separe por vírgula):")
        if outras_doencas:
            doencas.extend([d.strip() for d in outras_doencas.split(",")])

    st.markdown("---")
    st.markdown("**Análise Clínica da Triagem:**")

    if altura > 0:
        imc = peso / (altura**2)
        if imc < 23.0:
            status_imc = "Baixo Peso (Desnutrição)"
        elif imc <= 28.0:
            status_imc = "Eutrofia (Peso Normal para Idoso)"
        else:
            status_imc = "Sobrepeso / Obesidade"
        st.write(f"➡️ **IMC:** {imc:.2f} kg/m² — *{status_imc}*")
    else:
        imc = 0
        status_imc = "N/A"

    status_panturrilha = (
        "Normal"
        if panturrilha >= 31.0
        else "Alerta: Risco de Sarcopenia / Perda de Massa"
    )
    st.write(
        f"➡️ **Circunferência da Panturrilha:** {panturrilha} cm — "
        f"*{status_panturrilha}*"
    )

    status_pa = "Normal"
    if pa_sistolica >= 140 or pa_diastolica >= 90:
        status_pa = "Alterada (Hipertensão)"
    elif pa_sistolica < 90 or pa_diastolica < 60:
        status_pa = "Alterada (Hipotensão)"
    st.write(
        f"➡️ **Pressão Arterial:** {pa_sistolica}/{pa_diastolica} mmHg — *{status_pa}*"
    )

    if st.button("💾 Gravar Triagem Inicial", type="primary", use_container_width=True):
        dados_triagem = {
            "pontuacao": f"{pa_sistolica}/{pa_diastolica}",
            "resultado": (f"IMC: {status_imc} | Panturrilha: {status_panturrilha}"),
            "peso": peso,
            "altura": altura,
            "imc": round(imc, 2),
            "panturrilha": panturrilha,
            "frequencia_cardiaca": freq_cardiaca,  # 🌟 RESOLVIDO AQUI!
            "comorbidades": (", ".join(doencas) if doencas else "Nenhuma relatada"),
        }
        salvar_avaliacao(
            id_paciente,
            id_profissional,
            "Triagem Inicial (Clínica)",
            dados_triagem,
        )
        st.success("Triagem gravada com sucesso!")


def gestao_medicamentos_local(id_paciente, id_profissional):
    st.markdown("### 💊 Rotina Diária de Medicamentos (Padrão 24h)")
    st.write(
        "Cadastre o medicamento e especifique os horários exatos "
        "de administração ao longo do dia."
    )

    with st.form("form_medicamento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome_remedio = st.text_input(
                "Nome do Medicamento (Ex: Losartana, Metformina):"
            ).strip()
            dosagem = st.text_input(
                "Dosagem / Posologia (Ex: 50mg, 1 cp, 5 gotas):"
            ).strip()
        with col2:
            st.markdown("**Definição dos Horários (HH:MM):**")
            c_h1, c_h2, c_h3, c_h4 = st.columns(4)
            h1 = c_h1.text_input("Horário 1", placeholder="08:00").strip()
            h2 = c_h2.text_input("Horário 2", placeholder="14:00").strip()
            h3 = c_h3.text_input("Horário 3", placeholder="20:00").strip()
            h4 = c_h4.text_input("Horário 4", placeholder="--:--").strip()

        submetido = st.form_submit_button("➕ Adicionar Medicamento à Rotina")

    if submetido:
        if nome_remedio and dosagem:
            horarios_lista = [h for h in [h1, h2, h3, h4] if h]

            if not horarios_lista:
                st.warning("Especifique ao menos um horário!")
            else:
                horarios_formatados = ", ".join(horarios_lista)

                dados_remedio = {
                    "pontuacao": "Medicamento",
                    "resultado": (
                        f"{nome_remedio} ({dosagem}) - Horários: {horarios_formatados}"
                    ),
                    "nome": nome_remedio,
                    "dosagem": dosagem,
                    "horarios": horarios_formatados,
                }
                salvar_avaliacao(
                    id_paciente,
                    id_profissional,
                    "Medicamento Cadastrado",
                    dados_remedio,
                )
                st.success(
                    f"✓ {nome_remedio} adicionado para às {horarios_formatados}!"
                )
                st.rerun()
        else:
            st.error("Preencha o nome do medicamento e a dosagem.")
