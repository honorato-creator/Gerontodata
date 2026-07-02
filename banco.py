import sqlite3
import os

# --- 🛡️ CONFIGURAÇÃO DE SEGURANÇA ---
DB_PATH = "gerontodata.db"


def conectar_banco():
    """Conexão com timeout para evitar travamentos em acessos simultâneos."""
    return sqlite3.connect(DB_PATH, timeout=30)


def criar_tabelas():
    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profissionais (
                id_profissional INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                data_nascimento TEXT,
                cidade TEXT,
                telefone TEXT,
                endereco TEXT,
                profissao TEXT,
                registro_conselho TEXT,
                codigo_recuperacao TEXT,
                sessao_ativa TEXT,
                verificado INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pacientes (
                id_paciente INTEGER PRIMARY KEY AUTOINCREMENT,
                id_profissional INTEGER,
                nome TEXT NOT NULL,
                idade INTEGER,
                sexo TEXT,
                endereco TEXT,
                contato_emergencia TEXT,
                tratamentos TEXT,
                evolucao_clinica TEXT DEFAULT '',
                FOREIGN KEY(id_profissional) REFERENCES profissionais(id_profissional)
            )
        """)
        conn.commit()


# --- 🔐 FUNÇÕES DE SEGURANÇA ---
def cadastrar_usuario_completo(
    nome, email, senha, dt_nasc, cidade, tel, end, profissao, registro
):
    with conectar_banco() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO profissionais (nome, usuario, senha, data_nascimento, cidade, telefone, endereco, profissao, registro_conselho)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (nome, email, senha, dt_nasc, cidade, tel, end, profissao, registro),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def verificar_login(usuario, senha):
    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_profissional, nome, usuario FROM profissionais WHERE usuario = ? AND senha = ?",
            (usuario, senha),
        )
        return cursor.fetchone()


def salvar_evolucao_paciente(id_paciente, texto_evolucao):
    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pacientes SET evolucao_clinica = ? WHERE id_paciente = ?",
            (texto_evolucao, id_paciente),
        )
        conn.commit()
        return True


# AGORA CORRETA: Identação alinhada com as outras funções
def buscar_evolucao(id_paciente):
    """Busca apenas o texto da evolução de um paciente específico."""
    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT evolucao_clinica FROM pacientes WHERE id_paciente = ?",
            (id_paciente,),
        )
        resultado = cursor.fetchone()
        return resultado[0] if resultado else ""


def salvar_paciente(id_profissional, nome):
    """Salva um novo paciente básico."""
    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pacientes (id_profissional, nome) VALUES (?, ?)",
            (id_profissional, nome),
        )
        conn.commit()


def deletar_profissional(id_profissional):
    """Remove um profissional e todos os dados vinculados a ele."""
    with conectar_banco() as conn:
        cursor = conn.cursor()

        # 1. Pega todos os IDs de pacientes deste profissional
        cursor.execute(
            "SELECT id_paciente FROM pacientes WHERE id_profissional = ?",
            (id_profissional,),
        )
        pacientes = cursor.fetchall()

        # 2. Deleta avaliações dos pacientes dele
        for p in pacientes:
            cursor.execute("DELETE FROM avaliacoes WHERE id_paciente = ?", (p[0],))

        # 3. Deleta os pacientes dele
        cursor.execute(
            "DELETE FROM pacientes WHERE id_profissional = ?", (id_profissional,)
        )

        # 4. Deleta o profissional
        cursor.execute(
            "DELETE FROM profissionais WHERE id_profissional = ?", (id_profissional,)
        )

        conn.commit()
        return True


def criar_tabela_feedback():
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


# Executa a criação
criar_tabela_feedback()
import sqlite3


def inicializar_banco():
    conn = sqlite3.connect("gerontodata.db")
    cursor = conn.cursor()

    # Tabela de Clínicas (Tenant)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clinicas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cnpj TEXT UNIQUE
    )""")

    # Tabela de Usuários com Hierarquia
    # cargo: 'admin' (dono da clínica) ou 'profissional'
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clinica_id INTEGER,
        nome TEXT,
        email TEXT UNIQUE,
        senha TEXT,
        cargo TEXT,
        FOREIGN KEY(clinica_id) REFERENCES clinicas(id)
    )""")

    conn.commit()
    conn.close()
