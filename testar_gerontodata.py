import sqlite3
import os
import banco
import escalas


def executar_testes_dinamicos():
    print("=" * 50)
    print("🚀 INICIANDO TESTES DO GERONTODATA (MULTI-TENANT & N8N)")
    print("=" * 50)

    # URL de teste do teu n8n (Substitui pela tua URL real do n8n se desejares)
    # Exemplo: "https://seu-n8n.com/webhook-test/gerontodata-webhook"
    URL_N8N_TESTE = "https://shadeseekingfruitfly-n8n.cloudfy.live/webhook-test/gerontodata-webhook"  # Usamos esta URL pública apenas para testar se o envio HTTP funciona!
    if os.path.exists("gerontodata.db"):
        try:
            os.remove("gerontodata.db")
            print("🧹 Banco de dados antigo removido para recriação limpa.")
        except Exception as e:
            print(f"⚠️ Não foi possível remover o banco antigo: {e}")

    # 2. Inicializa o banco (Criando a nova tabela integracoes_clinica)
    try:
        banco.criar_tabelas()
        print("✅ Tabelas criadas/verificadas com sucesso no SQLite.")
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return

    # 3. Cria Clínica, Profissional e vincula a Integração do n8n
    conn = sqlite3.connect("gerontodata.db")
    cursor = conn.cursor()
    try:
        # Cadastra Clínica (ID 1)
        cursor.execute(
            "INSERT INTO clinicas (nome, cnpj) VALUES (?, ?)",
            ("Clínica Viva Bem", "12.345.678/0001-99"),
        )
        clinica_id = cursor.lastrowid

        # Cadastra Profissional vinculado à clínica (ID_profissional 1)
        cursor.execute(
            """
            INSERT INTO profissionais (clinica_id, nome, usuario, senha, cargo, verificado)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (clinica_id, "Dr. Kaio", "kaio_admin", "senha123", "admin", 1),
        )
        id_prof = cursor.lastrowid

        # Cadastra Paciente vinculado à mesma clínica
        cursor.execute(
            """
            INSERT INTO pacientes (id_profissional, clinica_id, nome, idade, sexo)
            VALUES (?, ?, ?, ?, ?)
        """,
            (id_prof, clinica_id, "Maria de Lourdes (Teste)", 78, "Feminino"),
        )
        id_pac = cursor.lastrowid

        # Cadastra a URL do n8n para esta Clínica
        cursor.execute(
            """
            INSERT INTO integracoes_clinica (clinica_id, url_webhook_n8n)
            VALUES (?, ?)
        """,
            (clinica_id, URL_N8N_TESTE),
        )

        conn.commit()
        print(
            f"✅ Clínica ID {clinica_id}, Profissional ID {id_prof} e Paciente ID {id_pac} criados."
        )
        print(f"🔗 URL do n8n vinculada à Clínica com sucesso!")

    except Exception as e:
        print(f"❌ Erro na inserção de dados de teste: {e}")
        return
    finally:
        conn.close()

    # 4. Testa o salvamento de uma escala e o disparo automático
    print("\n[Teste de Escala] Simulando preenchimento de teste...")
    dados_escala = {
        "pontuacao": 28,
        "resultado": "Excelente capacidade funcional",
        "observacoes": "Paciente ativa e lúcida.",
    }

    try:
        # Esta função irá salvar no banco e chamar o disparar_webhook_n8n por trás!
        sucesso = escalas.salvar_avaliacao(
            id_paciente=id_pac,
            id_profissional=id_prof,
            tipo_teste="Índice de Katz (ABVD)",
            detalhes=dados_escala,
        )

        if sucesso:
            print("✅ Sucesso: Avaliação gravada no banco e webhook disparado!")
        else:
            print("❌ Erro: Falha ao salvar ou ao processar o webhook.")

    except Exception as e:
        print(f"❌ Erro ao executar a rotina de escala: {e}")

    print("\n" + "=" * 50)
    print("🏁 TESTE CONCLUÍDO!")
    print("=" * 50)


if __name__ == "__main__":
    executar_testes_dinamicos()
