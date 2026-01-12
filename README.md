# 🤖 ADK RAG Example

Um sistema avançado de **Retrieval-Augmented Generation (RAG)** construído com a Google ADK (Agent Development Kit). Este projeto utiliza múltiplos agentes especializados para gerenciar uploads, indexação inteligente de documentos e busca semântica utilizando o modelo **Gemini 2.5 Flash**.

---

## 📌 Descrição

O **RAG Agent Example** transforma documentos estáticos em uma base de conhecimento interativa. Através de um fluxo de orquestração inteligente, o sistema identifica se o usuário deseja gerenciar arquivos ou realizar perguntas sobre o conteúdo, roteando a demanda para o agente mais capacitado.

### Principais Diferenciais
* **Orquestração Inteligente**: Identifica automaticamente intenções de upload vs. busca através da análise das mensagens do usuário e metadados da sessão.
* **Indexação Eficiente**: Evita a re-indexação de arquivos duplicados utilizando um sistema de hashing MD5 baseado no conteúdo do arquivo.
* **Respostas com Grounding**: O assistente de busca utiliza metadados de aterramento para citar fontes e responder exclusivamente com base nos documentos carregados.
* **Gestão de Estado**: Mantém um registro persistente de arquivos indexados e configurações do repositório em um arquivo local JSON.

---

## 🏗️ Arquitetura do Sistema

O projeto é dividido em módulos especializados para garantir escalabilidade:

* **`orchestrator.py`**: Atua como o roteador principal, decidindo se a requisição deve ir para o `FileManager` ou para o `SearchAssistant`.
* **`agent.py`**: Define a personalidade e as instruções críticas de cada agente (Prompts).
* **`tools/`**: Contém a lógica de execução das ferramentas:
    * `file_uploader_tools.py`: Lógica para criação de stores, hashing e upload de artefatos.
    * `search_file.py`: Integração com o modelo para realizar buscas semânticas dentro do File Search Store.

---

## 🛠️ Tecnologias Utilizadas

* **LLM**: Gemini 2.5 Flash.
* **Framework**: Google ADK (Agent Development Kit).
* **SDK**: Google GenAI Python SDK.
* **Storage**: Google File Search Stores.

---

## 🚀 Como Executar

### 1. Pré-requisitos
* Python 3.10+
* Google API Key (com acesso ao Gemini e File Search).

### 2. Configuração
Crie um arquivo `.env` baseado no seu ambiente:
```env
GOOGLE_API_KEY=sua_chave_aqui
STORE_NAME=nome_do_seu_projeto
DEMO_AGENT_MODEL=gemini-2.5-flash
```
### 3. Execução

```env 
adk web
```

### 4. Instalação e Uso
O sistema gerencia automaticamente o ciclo de vida dos arquivos:
- Envio: Envie um arquivo na interface.
- Indexação: O FileManager detecta o arquivo, gera o hash e o envia para o armazenamento seguro.
- Consulta: Faça perguntas sobre o conteúdo. O SearchAssistant buscará a resposta e citará a fonte.

### 📂 Estrutura de Pastas
```env 
rag_agent/
├── tools/
│   ├── __init__.py            # Configuração global do cliente e caminhos
│   ├── file_uploader_tools.py  # Indexação e gestão de artefatos
│   └── search_file.py         # Ferramenta de busca em documentos
├── agent.py                   # Definição e instruções dos agentes
├── orchestrator.py            # Lógica de roteamento e orquestração
├── file_store_config.json     # Estado local dos arquivos indexados
└── README.md
```

-----

Referencia: https://www.youtube.com/watch?v=h4tuLuzSjbA&t=412s