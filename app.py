import streamlit as st
import sqlite3
import base64
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
        
    # NOVO BOTÃO DE UPLOAD DE ARQUIVOS (Suporta PDF, Word e Imagens)
    arquivo_enviado = st.file_uploader(
        "Arraste ou selecione o arquivo do CNIS / Relatório Previdenciário (PDF, Word, JPG, PNG)", 
        type=["pdf", "docx", "txt", "png", "jpg", "jpeg"]
    )
    
    if st.button("🚀 Executar Triagem Inteligente"):
        if not api_key:
            st.error("Por favor, insira sua Chave de API do Claude na barra lateral esquerda.")
        elif not nome or not cpf:
            st.warning("Por favor, preencha o Nome e o CPF do cliente antes de iniciar.")
        elif not arquivo_enviado:
            st.warning("Por favor, anexe um arquivo (PDF, Word ou Imagem) para que o sistema possa analisar.")
        else:
            with st.spinner("O Claude está extraindo e analisando as informações do seu documento... Por favor, aguarde."):
                try:
                    client = Anthropic(api_key=api_key)
                    
                    # Prepara o arquivo enviado para a API
                    bytes_arquivo = arquivo_enviado.read()
                    extensao = arquivo_enviado.name.split(".")[-1].lower()
                    
                    # Definição do comportamento do Claude
                    prompt_sistema = """
                    Atue como um sistema especialista em Triagem Previdenciária Automatizada. Sua função é analisar o documento anexado (CNIS, CTPS ou extratos) e realizar uma varredura baseada no checklist técnico.
                    DIRETRIZ CRÍTICA: Você NUNCA deve concluir que o segurado 'não tem direito'. Se faltar dados ou requisitos, aponte como: 'Em razão de [elemento], considera-se que há uma pendência para considerar o benefício'.
                    
                    Formate a saída rigorosamente em Markdown com:
                    # 📊 RELATÓRIO DE TRIAGEM PREVIDENCIÁRIA
                    ## 1. Alertas Críticos (Pendências e Indicadores)
                    ## 2. Diagnóstico por Tópico do Checklist (1 a 10)
                    ## 3. Oportunidades de Prospecção / Teses Previdenciárias
                    ## 4. Plano de Ação & Próximos Passos
                    """
                    
                    # Se for imagem, envia como bloco de imagem nativo do Claude
                    if extensao in ["png", "jpg", "jpeg"]:
                        tipo_midia = f"image/{'jpeg' if extensao in ['jpg', 'jpeg'] else 'png'}"
                        base64_imagem = base64.b64encode(bytes_arquivo).decode("utf-8")
                        conteudo_mensagem = [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": tipo_midia,
                                            "data": base64_imagem
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": "Analise esta imagem de documento previdenciário de acordo com as regras estabelecidas."
                                    }
                                ]
                            }
                        ]
                    else:
                        # Se for PDF, Word ou Texto, lê o conteúdo textual e envia envolto em tags
                        texto_extraido = bytes_arquivo.decode("utf-8", errors="ignore")
                        conteudo_mensagem = [
                            {"role": "user", "content": f"<dados_documento>\n{texto_extraido}\n</dados_documento>"}
                        ]
                    
                    # Chamada oficial para a API do Claude 3.5 Sonnet
                    message = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=4000,
                        temperature=0.1,
                        system=prompt_sistema,
                        messages=conteudo_mensagem
                    )
                    
                    resultado_markdown = message.content.text
                    salvar_relatorio(nome, cpf, resultado_markdown)
                    st.success(f"Análise de {nome} concluída e salva com sucesso!")
                    st.markdown(resultado_markdown)
                    
                except Exception as e:
                    st.error(f"Erro ao processar o arquivo com a API do Claude: {e}")

with aba_historico:
    if 'visualizar_relatorio' in st.session_state:
        st.subheader(f"Relatório Salvo: {st.session_state['nome_visualizar']}")
        st.markdown(st.session_state['visualizar_relatorio'])
    else:
        st.info("Selecione um cliente no Histórico (barra lateral esquerda) para abrir o relatório que ficou salvo.")
