import sqlite3
import os
import hashlib
import hmac
import secrets

# --- 🛡️ CONFIGURAÇÃO DE SEGURANÇA -----
DB_PATH = "gerontodata.db"


def conectar_banco():
    """Conexão com timeout para evitar travamentos em acessos simultâneos."""
    return sqlite3.connect(DB_PATH, timeout=30)


# --- 🏥 GARANTE VÍNCULO COM UMA CLÍNICA ---
def garantir_clinica_do_profissional(id_profissional):
    """
    Todo o fluxo de integração com o n8n (webhook do WhatsApp) depende do
    profissional estar vinculado a uma clinica_id. Profissionais cadastrados
    sem essa informação (clinica_id NULL) nunca disparavam o webhook, mesmo
    com a URL configurada, porque o sistema não sabia em qual clínica buscar.
    Esta função cria uma clínica individual para o profissional na primeira
    vez que for necessário, e devolve o clinica_id (já existente ou recém-criado).
    """
    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT clinica_id, nome FROM profissionais WHERE id_profissional = ?",
            (id_profissional,),
        )
        linha = cursor.fetchone()
        if not linha:
            return None

        clinica_id, nome_prof = linha
        if clinica_id:
            return clinica_id

        cursor.execute("INSERT INTO clinicas (nome) VALUES (?)", (f"Clínica de {nome_prof}",))
        nova_clinica_id = cursor.lastrowid
        cursor.execute(
            "UPDATE profissionais SET clinica_id = ? WHERE id_profissional = ?",
            (nova_clinica_id, id_profissional),
        )
        conn.commit()
        return nova_clinica_id


# --- 🔐 SENHAS: hash + salt (nunca gravar senha em texto puro) ---
def _hash_senha(senha_texto_puro):
    salt = secrets.token_hex(16)
    hash_senha = hashlib.sha256((salt + senha_texto_puro).encode("utf-8")).hexdigest()
    return f"{salt}${hash_senha}"


def _verificar_senha(senha_texto_puro, senha_armazenada):
    # Compatibilidade: se a senha no banco ainda não tem o formato "salt$hash"
    # (dados antigos gravados em texto puro), compara direto por segurança mínima.
    if not senha_armazenada or "$" not in senha_armazenada:
        return hmac.compare_digest(senha_texto_puro, senha_armazenada or "")
    salt, hash_salvo = senha_armazenada.split("$", 1)
    hash_calculado = hashlib.sha256((salt + senha_texto_puro).encode("utf-8")).hexdigest()
    return hmac.compare_digest(hash_calculado, hash_salvo)


def criar_tabelas():
    with conectar_banco() as conn:
        cursor = conn.cursor()

        # 1. Tabela de Clínicas (Tenant do SaaS)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clinicas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cnpj TEXT UNIQUE
            )
        """)

        # 2. Tabela de Profissionais / Usuários (Com clinica_id e Cargo)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profissionais (
                id_profissional INTEGER PRIMARY KEY AUTOINCREMENT,
                clinica_id INTEGER,
                nome TEXT NOT NULL,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                cargo TEXT DEFAULT 'profissional', -- 'admin' ou 'profissional'
                data_nascimento TEXT,
                cidade TEXT,
                telefone TEXT,
                endereco TEXT,
                profissao TEXT,
                registro_conselho TEXT,
                codigo_recuperacao TEXT,
                sessao_ativa TEXT,
                verificado INTEGER DEFAULT 0,
                FOREIGN KEY(clinica_id) REFERENCES clinicas(id)
            )
        """)

        # 3. Tabela de Pacientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pacientes (
                id_paciente INTEGER PRIMARY KEY AUTOINCREMENT,
                id_profissional INTEGER,
                clinica_id INTEGER, -- Segregação SaaS
                nome TEXT NOT NULL,
                idade INTEGER,
                sexo TEXT,
                endereco TEXT,
                contato_emergencia TEXT,
                tratamentos TEXT,
                evolucao_clinica TEXT DEFAULT '',
                FOREIGN KEY(id_profissional) REFERENCES profissionais(id_profissional),
                FOREIGN KEY(clinica_id) REFERENCES clinicas(id)
            )
        """)

        # Migração: adiciona a coluna do WhatsApp de destino em bancos que já
        # existiam antes dela (CREATE TABLE IF NOT EXISTS não altera tabelas
        # já criadas). Só ignoramos o erro esperado (coluna já existe) -
        # qualquer outro problema real (ex: banco somente-leitura) agora
        # aparece de verdade em vez de ficar escondido em silêncio.
        try:
            cursor.execute("ALTER TABLE pacientes ADD COLUMN whatsapp_responsavel TEXT")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise

        # 4. Tabela de Avaliações
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS avaliacoes (
                id_avaliacao INTEGER PRIMARY KEY AUTOINCREMENT,
                id_paciente INTEGER,
                id_profissional INTEGER,
                tipo TEXT NOT NULL,
                data TEXT NOT NULL,
                detalhes TEXT,
                FOREIGN KEY(id_paciente) REFERENCES pacientes(id_paciente),
                FOREIGN KEY(id_profissional) REFERENCES profissionais(id_profissional)
            )
        """)

        # 4b. Tabela de Histórico de Escalas (usada pela DUREL em escalas.py)
        #     Faltava no schema original -> salvar_avaliacao da DUREL quebrava.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_escalas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER,
                escala_nome TEXT NOT NULL,
                resultado TEXT,
                data TEXT NOT NULL,
                FOREIGN KEY(paciente_id) REFERENCES pacientes(id_paciente)
            )
        """)

        # 5. Tabela de Feedbacks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                tipo TEXT,
                mensagem TEXT,
                data TEXT
            )
        """)

        # 6. Tabela de Configurações de Integração por Clínica
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS integracoes_clinica (
                clinica_id INTEGER PRIMARY KEY,
                url_webhook_n8n TEXT,
                FOREIGN KEY(clinica_id) REFERENCES clinicas(id)
            )
        """)

        conn.commit()


def deletar_profissional_completo(id_profissional):
    with conectar_banco() as conn:
        cursor = conn.cursor()

        # 1. Deleta as avaliações dos pacientes vinculados ao profissional
        cursor.execute(
            """
            DELETE FROM avaliacoes 
            WHERE id_profissional = ?
        """,
            (id_profissional,),
        )

        # 2. Deleta os pacientes do profissional
        cursor.execute(
            """
            DELETE FROM pacientes 
            WHERE id_profissional = ?
        """,
            (id_profissional,),
        )

        # 3. Deleta o profissional
        cursor.execute(
            """
            DELETE FROM profissionais 
            WHERE id_profissional = ?
        """,
            (id_profissional,),
        )

        conn.commit()
        return True


# gerontodata.py chama "banco.deletar_profissional" (sem o sufixo "_completo").
# Mantendo os dois nomes para não quebrar nada que já dependa do original.
def deletar_profissional(id_profissional):
    return deletar_profissional_completo(id_profissional)


# --- 🔑 LOGIN ---
def verificar_login(usuario, senha):
    """
    Confere usuário/senha na tabela profissionais.
    Retorna (id_profissional, nome, usuario) se as credenciais forem válidas,
    ou None caso contrário.
    """
    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_profissional, nome, usuario, senha FROM profissionais WHERE usuario = ?",
            (usuario,),
        )
        linha = cursor.fetchone()

    if not linha:
        return None

    id_profissional, nome, usuario_db, senha_hash = linha

    if not _verificar_senha(senha, senha_hash):
        return None

    return (id_profissional, nome, usuario_db)


# --- 📝 CADASTRO DE PROFISSIONAL ---
def cadastrar_usuario_completo(
    nome,
    email,
    senha,
    data_nascimento,
    cidade,
    telefone,
    endereco,
    profissao,
    registro_conselho,
    clinica_id=None,
):
    """
    Cadastra um novo profissional com senha protegida por hash.
    Retorna True em sucesso, False se o e-mail (usuario) já existir.
    """
    senha_hash = _hash_senha(senha)
    try:
        with conectar_banco() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO profissionais
                    (clinica_id, nome, usuario, senha, cargo, data_nascimento,
                     cidade, telefone, endereco, profissao, registro_conselho, verificado)
                VALUES (?, ?, ?, ?, 'profissional', ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    clinica_id,
                    nome,
                    email,
                    senha_hash,
                    data_nascimento,
                    cidade,
                    telefone,
                    endereco,
                    profissao,
                    registro_conselho,
                ),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        # UNIQUE(usuario) violado -> e-mail já cadastrado
        return False


# --- 👤 PACIENTES ---
def cadastrar_paciente(nome, idade, sexo, clinica_id=None, id_profissional=None):
    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pacientes (id_profissional, clinica_id, nome, idade, sexo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (id_profissional, clinica_id, nome, idade, sexo),
        )
        conn.commit()
        return cursor.lastrowid


def salvar_evolucao_paciente(id_paciente, texto_evolucao):
    with conectar_banco() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pacientes SET evolucao_clinica = ? WHERE id_paciente = ?",
            (texto_evolucao, id_paciente),
        )
        conn.commit()
        return True


# --- 📋 AVALIAÇÕES (usada por salvar_avaliacao_com_webhook em gerontodata.py) ---
def salvar_avaliacao(
    paciente_id, profissional_id, clinica_id, tipo_escala, pontuacao, interpretacao, respostas
):
    """
    Também estava faltando: gerontodata.py chama banco.salvar_avaliacao com essa
    assinatura (diferente da salvar_avaliacao que já existe em escalas.py).
    """
    try:
        detalhes = {
            "pontuacao": pontuacao,
            "resultado": interpretacao,
            "respostas": respostas,
        }
        with conectar_banco() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO avaliacoes (id_paciente, id_profissional, tipo, data, detalhes)
                VALUES (?, ?, ?, date('now'), ?)
                """,
                (paciente_id, profissional_id, tipo_escala, str(detalhes)),
            )
            conn.commit()
        return True
    except Exception:
        return False


# Executa as migrações na inicialização do script
criar_tabelas()