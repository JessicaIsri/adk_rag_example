
import json
from typing import Dict, Any
from google.genai import types
from google.adk.tools import FunctionTool, ToolContext

from rag_agent.tools import CONFIG_PATH, client, api_key


def load_file_store_config() -> Dict[str, Any]:
    """Carrega as informações do storage"""

    if not CONFIG_PATH.exists():
        return {
            'error': True,
            'message': 'No file store configured. Please run setup_file_store.py first.'
        }

    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def search_documents(query: str, tool_context: ToolContext) -> Dict[str, Any]:
    config = load_file_store_config()

    if config.get('error'):
        return {
            "status": "error",
            "message": config['message'],
            "answer": "",
            "sources": [],
            "query": query
        }

    store_name = config.get('file_search_store_name')
    indexed_files = config.get('uploaded_files', [])

    if not store_name:
        return {
            "status": "error",
            "message": "File store name not found in configuration",
            "answer": "",
            "sources": [],
            "query": query
        }

    try:

        if not api_key:
            return {
                "status": "error",
                "message": "Neither FILE_SEARCH_API_KEY nor GOOGLE_API_KEY found in environment",
                "answer": "",
                "sources": [],
                "query": query
            }


        print(f"[FileSearch] Searching in store: {store_name}")
        print(f"[FileSearch] Query: {query}")

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_name]
                    )
                )]
            )
        )

        sources = []
        if response.candidates and response.candidates[0].grounding_metadata:
            grounding = response.candidates[0].grounding_metadata
            sources = [
                c.retrieved_context.title
                for c in grounding.grounding_chunks
                if hasattr(c, 'retrieved_context') and hasattr(c.retrieved_context, 'title')
            ]

        print(f"[FileSearch] Found {len(sources)} source(s)")

        tool_context.state['last_search'] = {
            "query": query,
            "found_sources": len(sources),
            "indexed_files": indexed_files
        }

        return {
            "status": "success",
            "answer": response.text,
            "sources": list(set(sources)),  # Remove duplicates
            "query": query,
            "indexed_files": indexed_files
        }

    except Exception as e:
        error_msg = f"Search failed: {str(e)}"
        print(f"[FileSearch] Error: {error_msg}")

        return {
            "status": "error",
            "message": error_msg,
            "answer": "",
            "sources": [],
            "query": query
        }


search_tool = FunctionTool(search_documents)