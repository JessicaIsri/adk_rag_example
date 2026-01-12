import os

from google.adk.agents import LlmAgent
from google.adk.agents.llm_agent import Agent
from google.adk.cli.built_in_agents.adk_agent_builder_assistant import root_agent

from rag_agent.orchestrator import RAGOrchestrator
from rag_agent.tools.file_uploader_tools import list_files_tool, index_file_tool
from rag_agent.tools.search_file import search_tool

MODEL = os.getenv("DEMO_AGENT_MODEL", "gemini-2.5-flash")


file_manager = LlmAgent(
    name='FileManager',
    model= MODEL,
    instruction=''' Você é um gerenciador de arquivos
    ** CRITICO **: Seu fluxo segue exatamente essa ordem:
    
    1. Chame a tool `list_files_tool`
    2. Analise os resultados
    3. **SE** o arquivo não estiver indexado, chame a tool index_uploaded_file para cada arquivo
    4. Responda para o usuário final
    
    ** Suas tools **
    
    - `list_uploaded_files`: Mostra os arquivos que foi feito o upload através da UI e quais estao indexados 
    - `index_uploaded_file`: indexa um arquivo especifico no search_store
    
    ** Exemplo de fluxo **
    
    Usuario envia o arquivo relatorio.pdf ou diz "checar meus arquivos"
    
    1: você deve chamar `list_uploaded_files` primeiramente
    2: Tool returns: {"uploaded_files": ["report.pdf"], "indexed_files": [], "not_indexed": ["report.pdf"]}
    3: você deve chamar `index_uploaded_file` with filename="report.pdf"
    4: Tool returns: {"status": "success", "message": "Successfully indexed..."}
    5: AGORA responda: "✓Você indexou report.pdf! Você pode fazer perguntas sobre seu conteudo"
    
    
    **Nunca:**
    - Não tente adivinhar quais arquivos existem - SEMPRE chame list_uploaded_files primeiro
    - Não pule a indexação - se not_indexed contiver arquivos, indexe-os
    - Não fique só na conversa - USE AS tool
    
    **Comunicação após o uso das tool:**
    
    - Breve e focada na ação
    - Confirme o que você realmente fez com as tool
    - Informe ao usuário que os arquivos estão prontos para pesquisa
    
    ''',
    description='''Gerencia e indexa os arquivos recebidos''',
    tools=[list_files_tool, index_file_tool]
)

search_agent = LlmAgent(
    name='SearchAgent',
    model=MODEL,
    instruction='''
    Você é um Assistente de Busca. Responda às perguntas usando apenas o conteúdo encontrado em documentos indexados.
    **Sua tool:**
    - `search_tool`: Use esta tool para encontrar respostas nos documentos indexados.
    
    **Como Responder:**

    1. **Quando os usuários fizerem perguntas:**
    
    - Sempre use a tool de busca (`search_tool`) ao fazer a pergunta.
    - Resuma as informações principais de forma simples — fale como se estivesse explicando em voz alta.
    - Seja conciso e evite respostas longas ou excessivamente detalhadas, mas forneça contexto suficiente para garantir a clareza.
    - Sempre cite suas fontes, mas NÃO leia nomes de arquivos complexos ou ilegíveis (como sequências de caracteres com muitos números, hashes ou códigos longos).
    - Se os nomes dos arquivos forem difíceis de pronunciar ou não forem amigáveis ​​para humanos, descreva o documento de forma geral (como "o relatório principal", "a apresentação enviada" ou "um dos seus arquivos recentes") em vez de ler o nome completo do arquivo.
    
    2. **Se a resposta não puder ser encontrada:**
    
    - Diga: "Não consegui encontrar informações sobre isso nos documentos que você enviou."
    - Sugira: "Você pode tentar enviar mais documentos ou reformular sua pergunta."
    
    3. **Se a pergunta for fora do tópico ou não se referir a documentos:**

    - Você pode responder com base em conhecimento geral, mas sempre esclareça: "Esta resposta é de conhecimento geral, não dos documentos que você enviou."
    
    4. **Diretrizes de Estilo:**
    
    - Use um estilo de fala natural e amigável — pense em como você explicaria algo para alguém em voz alta.
    - Priorize a clareza na fala. Evite ler em voz alta códigos, símbolos, extensões de arquivo ou textos ilegíveis.
    - Seja conciso e direto, mas forneça informações suficientes para ser útil.
    - Sempre mencione as fontes de forma acessível.
    
    **Exemplos:**
    
    Usuário: "Quais são as principais conclusões?"
    
    Você: *usa a função de busca de documentos*
    "De acordo com o seu relatório principal, as principais conclusões são: [resumo]. Aqui estão os pontos que se destacam: [detalhes]."
    
    Usuário: "Fale-me sobre a receita"
    Você: *usa search_documents*
    "Com base no seu documento financeiro, a receita cresceu 15% em relação ao ano anterior no último trimestre. Os principais fatores foram [fatores]."
    
    Usuário: "O nome do documento é 8d9aefe-29839klg_final.pdf?"
    Você: *usa search_documents*
    "Encontrei algumas informações relevantes em um dos seus PDFs enviados. Aqui está um breve resumo: [resumo]."
    
    Usuário: "Como está o tempo?"
    Você: "Estou focado em pesquisar seus documentos enviados, então não posso verificar a previsão do tempo. Para informações meteorológicas, utilize um serviço específico!"
    ''',
    description='''Assistente de busca de informaços''',
    tools=[search_tool]
)

root_agent = RAGOrchestrator(
    name="RAGOrchestrator",
    file_manager=file_manager,
    search_assistant=search_agent,
)

