import streamlit as st
import sqlite3
from anthropic import Anthropic
from datetime import datetime

# 1. CONFIGURAÇÃO DO BANCO DE DADOS LOCAL (SQLite)
def iniciar_banco():
    conn = sqlite3.connect('clientes_prev.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relatorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL,
            data_analise TEXT NOT NULL,
            relatorio_txt TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def salvar_relatorio(nome, cpf, relatorio):
    conn = sqlite3.connect('clientes_prev.db')
    cursor = conn.cursor()
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    cursor.execute(
        "INSERT INTO relatorios (nome, cpf, data_analise, relatorio_txt) VALUES (?, ?, ?, ?)",
        (nome, cpf, data_atual, relatorio)
    )
    conn.commit()
    conn.close()

def listar_relatorios():
    conn = sqlite3.connect('clientes_prev.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, cpf, data_analise, relatorio_txt FROM relatorios ORDER BY id DESC")
    dados = cursor.fetchall()
    conn.close()
    return dados

iniciar_banco()

# 2. INTERFACE DO USUÁRIO (Streamlit)
st.set_page_config(page_title="Triagem Previdenciária IA", layout="wide", page_icon="⚖️")
st.title("⚖️ Sistema de Triagem Previdenciária Automatizada")

# Barra lateral
with st.sidebar:
    st.header("🔑 Configuração")
    api_key = st.text_input("Chave de API do Claude (Anthropic API Key)", type="password", help="Insira sua chave secreta da API do Claude")
    
    st.divider()
    st.header("📂 Histórico de Clientes")
    historico = listar_relatorios()
    
    if not historico:
        st.info("Nenhum cliente analisado ainda.")
    else:
        for item in historico:
            id_rel, nome_cli, cpf_cli, data_cli, texto_cli = item
            if st.button(f"👤 {nome_cli} ({data_cli})", key=f"cli_{id_rel}"):
                st.session_state['visualizar_relatorio'] = texto_cli
                st.session_state['nome_visualizar'] = nome_cli

# Painel Principal (Abas)
aba_nova, aba_historico = st.tabs(["🆕 Nova Análise", "📖 Visualizar Relatório Selecionado"])

with aba_nova:
    st.subheader("Inserir Dados do Cliente")
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome Completo do Cliente")
    with col2:
        cpf = st.text_input("CPF (Apenas números)")
        
    dados_cnis = st.text_area("Cole aqui o texto do CNIS / Relatórios Previdenciários", height=300)
    
    if st.button("🚀 Executar Triagem Inteligente"):
        if not api_key:
            st.error("Por favor, insira sua Chave de API do Claude na barra lateral esquerda.")
        elif not nome or not cpf or not dados_cnis:
            st.warning("Preencha todos os campos (Nome, CPF e texto do CNIS) antes de iniciar.")
        else:
            with st.spinner("O Claude está analisando o CNIS linha por linha... Por favor, aguarde."):
                try:
                    client = Anthropic(api_key=api_key)
                    
                    prompt_sistema = """
                    Atue como um sistema especialista em Triagem Previdenciária Automatizada. Sua função é receber o CNIS e realizar uma varredura baseada no checklist.
                    DIRETRIZ CRÍTICA: Você NUNCA deve concluir que o segurado 'não tem direito'. Se faltar dados ou requisitos, aponte como: 'Em razão de [elemento], considera-se que há uma pendência para considerar o benefício'.
                    
                    Formate a saída rigorosamente em Markdown com:
                    # 📊 RELATÓRIO DE TRIAGEM PREVIDENCIÁRIA
                    ## 1. Alertas Críticos (Pendências e Indicadores)
                    ## 2. Diagnóstico por Tópico do Checklist (1 a 10)
                    ## 3. Oportunidades de Prospecção / Teses Previdenciárias
                    ## 4. Plano de Ação & Próximos Passos
                    """
                    
                    message = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=4000,
                        temperature=0.1,
                        system=prompt_sistema,
                        messages=[
                            {"role": "user", "content": f"<dados_cnis>\n{dados_cnis}\n</dados_cnis>"}
                        ]
                    )
                    
                    resultado_markdown = message.content.text
                    salvar_relatorio(nome, cpf, resultado_markdown)
                    st.success(f"Análise de {nome} concluída e salva com sucesso!")
                    st.markdown(resultado_markdown)
                    
                except Exception as e:
                    st.error(f"Erro ao processar com a API do Claude: {e}")

with aba_historico:
    if 'visualizar_relatorio' in st.session_state:
        st.subheader(f"Relatório Salvo: {st.session_state['nome_visualizar']}")
        st.markdown(st.session_state['visualizar_relatorio'])
    else:
        st.info("Selecione um cliente no Histórico (barra lateral esquerda) para abrir o relatório que ficou salvo.")
