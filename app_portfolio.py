import streamlit as st

st.set_page_config(
    page_title="Kaio Honorato | Portfólio", page_icon="🚀", layout="centered"
)

# --- CSS customizado (Com correção de contraste para Dark/Light Mode) ---
st.markdown(
    """
<style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #E67E22; color: white; }
    .card { 
        background-color: #FFFFFF; 
        padding: 25px; 
        border-radius: 10px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        margin-bottom: 20px;
        color: #1A252F !important; /* Força o texto interno a ficar escuro e visível */
    }
    .card p {
        color: #34495E !important; /* Força a descrição a ficar legível */
    }
    .card h4 {
        color: #E67E22 !important; /* Título do projeto em laranja */
        margin-top: 0;
    }
    h1, h2, h3 { color: #ffffff; }
</style>
""",
    unsafe_allow_html=True,
)

# --- Cabeçalho ---
col1, col2 = st.columns([1, 3])
with col1:
    st.image(
        "https://ui-avatars.com/api/?name=Kaio+Honorato&background=E67E22&color=fff&size=200",
        width=120,
    )
with col2:
    st.title("Kaio Honorato")
    st.write("Desenvolvedor Python & Arquiteto de Soluções SaaS")

st.markdown("---")

# --- Projeto Destaque ---
st.markdown("### 🚀 Projeto Principal")
st.markdown(
    """
<div class="card">
    <h4>GerontoData Premium</h4>
    <p>Plataforma completa de gestão para avaliação multidisciplinar do idoso. Desenvolvida com foco em automação clínica, banco de dados relacional e exportação de relatórios inteligentes.</p>
</div>
""",
    unsafe_allow_html=True,
)

# Botão nativo do Streamlit para abrir o link
st.link_button("🔥 Acessar GerontoData Premium", "https://gerontodata.streamlit.app/")

st.markdown("---")

# --- Skills ---
st.subheader("🛠️ Minhas Tecnologias")
cols = st.columns(4)
skills = ["Python", "Pandas", "SQLite", "Streamlit"]
for i, skill in enumerate(skills):
    cols[i % 4].info(skill)

st.markdown("---")

# --- 🦊 EASTER EGG: MODO HOKAGE ---
st.markdown("---")
st.caption("⚡ Área do Desenvolvedor")

# Dica sutil para quem for curioso
st.markdown(
    "<p style='font-size: 10px; color: #888;'>Dica: todo shinobi da folha sonha em ser... tente digitar o seu nível no terminal abaixo.</p>",
    unsafe_allow_html=True,
)

segredo = st.text_input("Insira a chave de acesso:", placeholder="???", key="ninja_key")

if segredo.lower() == "hokage":
    st.balloons()
    st.success("🥷 Estilo Python: Jutsu Clones da Automação Ativado!")
    st.markdown(
        """
    <div class="card" style='border-left: 5px solid #FF7A00;'>
        <h4 style='color: #FF7A00; margin-top: 0;'>🔥 O Hokage das Automações</h4>
        <p><strong>"Eu nunca desisto dos meus códigos, esse é o meu jeito ninja!"</strong></p>
        <p>Seja escalando microsserviços, otimizando rotas complexas ou blindando bancos de dados na nuvem, a missão é entregar soluções lendárias.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.markdown("---")
st.caption("Desenvolvido por Kaio Honorato | 2026")
