import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

from google import genai
from google.adk.tools import ToolContext, FunctionTool

from rag_agent.tools import CONFIG_PATH, client, STORE_NAME, api_key


def create_or_load_file_search_store():
    """Cria um novo file store caso não exista um com a nomeclatura definida"""
    file_search_store = None
    for store in client.file_search_stores.list():
        if store.display_name == STORE_NAME:
            file_search_store = store
            print(f"Found existing store at {file_search_store.name}")
            print(f"Total docs: {file_search_store.active_documents_count}")
            return file_search_store.name

    if file_search_store is None:
        print("Store not found. Creating new store...")
        try:
            # Create the store...
            file_search_store = client.file_search_stores.create(config={'display_name': STORE_NAME})
            print(f"Store created: {file_search_store.name}")
        except Exception as e:
            print(f"Error creating store: {e}")
            return file_search_store.name
    print(f"LOG FILE SEARCH: {file_search_store}")


def load_or_create_config() -> Dict[str, Any]:
    """Carrega a configuração caso exista, caso contrario cria uma nova"""

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)

    return {
        'file_search_store_name': None,
        'uploaded_files': []
    }

def save_config(config: Dict[str, Any]):
    """Salva o estado da configuração no arquivo.
    essa etapa é utilizada para evitar a re-indexação de arquivos"""
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def generate_filename_from_content(file_data: bytes, mime_type: str) -> str:
    """
    Gera uma nomeclatura unica baseada no hash do arquivo

    ou seja, arquivos iguais possuem o mesmo hash, garantindo que nao sejam re-indexados

    Args:
        file_data: o arquivo binario
        mime_type: o MIME type (e.g., "application/pdf")

    Returns:
        A filename como "doc_a1b2c3d4e5f6.pdf"
    """

    content_hash = hashlib.md5(file_data).hexdigest()[:12]  # Use first 12 chars of MD5
    ext_map = {
        'application/pdf': 'pdf',
        'application/msword': 'doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'text/plain': 'txt',
        'text/markdown': 'md',
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'image/jpg': 'jpg',
    }


    if '/' in mime_type:
        mime_ext = mime_type.split('/')[-1]
        if mime_ext in ['pdf', 'png', 'jpg', 'jpeg', 'txt', 'md']:
            ext = mime_ext
        else:
            ext = ext_map.get(mime_type, mime_ext)
    else:
        ext = ext_map.get(mime_type, 'bin')

    return f"doc_{content_hash}.{ext}"

async def uploaded_file_list(tool_context: ToolContext) -> Dict[str, Any]:
    print(f"[FileUpload] ====== uploaded_file_list CALLED ======")
    try:
        uploaded_files = await tool_context.list_artifacts()
        print(f"[FileUpload] {uploaded_files} uploaded files")
        inline_uploads = []

        if hasattr(tool_context, '_invocation_context'):
            ctx = tool_context._invocation_context
            if ctx and ctx.session and ctx.session.events:
                for event in reversed(ctx.session.events[-5:]):  # Check last 5 events
                    if event.content and event.content.parts:
                        for idx, part in enumerate(event.content.parts):
                            if part.inline_data:
                                file_data = part.inline_data.data
                                mime_type = part.inline_data.mime_type

                                filename = generate_filename_from_content(file_data, mime_type)
                                if filename not in inline_uploads:
                                    inline_uploads.append(filename)
                                    print(
                                        f"[FileUpload] Found inline upload: {filename} ({mime_type}, {len(file_data)} bytes)")
        # Combina o arquivo carregado aos previamente carregados
        all_files = list(set(uploaded_files + inline_uploads))
        print(f"[FileUpload] Total files available: {len(all_files)} - {all_files}")


        config = load_or_create_config()
        indexed_files = config.get('uploaded_files', [])

        # Localiza os arquivos que nao estao indexados ainda
        not_indexed = [f for f in all_files if f not in indexed_files]

        message = f"Found {len(all_files)} uploaded file(s)"
        if not_indexed:
            message += f", {len(not_indexed)} need indexing: {', '.join(not_indexed)}"
        if indexed_files:
            message += f", {len(indexed_files)} already indexed"

        return {
            "status": "success",
            "uploaded_files": all_files,
            "indexed_files": indexed_files,
            "not_indexed": not_indexed,
            "message": message,
            "store_name": config.get('file_search_store_name')
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list files: {str(e)}",
            "uploaded_files": [],
            "indexed_files": [],
            "not_indexed": []
        }

async def index_uploaded_file(filename: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Indexa um arquivo carregado através da interface web do ADK.

    Esta ferramenta recebe um arquivo carregado pela interface web (armazenado como um artefato)
    e o indexa no repositório de busca de arquivos para que possa ser pesquisado.

    Args:
        filename: o nome do arquivo feito upload (e.g., "document.pdf")
        tool_context: o contexto da ferramenta

    Returns:
        Um dicionario contendo:
        - status: "success" ou "error"
        - message: Descrição do evento
        - filename: o arquivo indexado
        - store_name: O file search store
    """

    print(f"[FileUpload] ====== index_uploaded_file CALLED with filename='{filename}' ======")

    try:

        if not api_key:
            return {
                "status": "error",
                "message": "No API key found in environment",
                "filename": filename
            }

        # Carrega a configuração previa do storage
        config = load_or_create_config()
        store_name = config.get('file_search_store_name')

        # Cria o store caso não exista
        if not store_name:
            store_name = create_or_load_file_search_store()
            config['file_search_store_name'] = store_name
            config['uploaded_files'] = []
            config['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            save_config(config)


        print(f"[FileUpload] Loading artifact: {filename}")
        artifact_part = await tool_context.load_artifact(filename)

        file_data = None
        mime_type = None

        if artifact_part and artifact_part.inline_data:
            # Found in artifact storage
            file_data = artifact_part.inline_data.data
            mime_type = artifact_part.inline_data.mime_type
            print(f"[FileUpload] Loaded from artifact storage")
        else:
            print(f"[FileUpload] Not in storage, checking session history for inline uploads...")
            if hasattr(tool_context, '_invocation_context'):
                ctx = tool_context._invocation_context
                if ctx and ctx.session and ctx.session.events:
                    # Check recent events for inline_data
                    for event in reversed(ctx.session.events[-5:]):
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if part.inline_data:
                                    # Found inline data!
                                    file_data = part.inline_data.data
                                    mime_type = part.inline_data.mime_type
                                    print(f"[FileUpload] Loaded from session inline_data: {mime_type}")
                                    break
                        if file_data:
                            break

        if not file_data or not mime_type:
            available = await tool_context.list_artifacts()
            return {
                "status": "error",
                "message": f"File '{filename}' not found in storage or session history. Available artifacts: {available}",
                "filename": filename
            }


        actual_filename = generate_filename_from_content(file_data, mime_type)
        print(f"[FileUpload] Generated filename from content: {actual_filename} (original: {filename})")


        if actual_filename in config.get('uploaded_files', []):
            return {
                "status": "already_indexed",
                "message": f"File '{actual_filename}' is already indexed (same content detected)",
                "filename": actual_filename,
                "store_name": store_name
            }

        print(f"[FileUpload] File size: {len(file_data)} bytes, MIME: {mime_type}")


        temp_dir = Path(tempfile.gettempdir()) / "rag_uploads"
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / actual_filename

        with open(temp_file, 'wb') as f:
            f.write(file_data)

        # Upload to file search store
        client = genai.Client(api_key=api_key)

        print(f"[FileUpload] Uploading to store: {store_name}")
        upload_op = client.file_search_stores.upload_to_file_search_store(
            file_search_store_name=store_name,
            file=str(temp_file)
        )


        timeout = 120  # 2 minutes
        elapsed = 0
        while not upload_op.done and elapsed < timeout:
            time.sleep(3)
            elapsed += 3
            upload_op = client.operations.get(upload_op)
            print(f"[FileUpload] Uploading... {elapsed}s")

        if not upload_op.done:
            return {
                "status": "error",
                "message": f"Upload timed out after {timeout}s",
                "filename": actual_filename
            }


        config['uploaded_files'].append(actual_filename)
        save_config(config)

        # armazenando o estado do contexto
        tool_context.state['last_indexed_file'] = actual_filename
        tool_context.state['indexed_files'] = config['uploaded_files']

        print(f"[FileUpload] Successfully indexed: {actual_filename}")

        return {
            "status": "success",
            "message": f"Successfully indexed '{actual_filename}' into the search store",
            "filename": actual_filename,
            "store_name": store_name,
            "total_indexed": len(config['uploaded_files'])
        }

    except Exception as e:
        error_msg = f"Failed to index file: {str(e)}"
        print(f"[FileUpload] Error: {error_msg}")

        return {
            "status": "error",
            "message": error_msg,
            "filename": filename
        }


list_files_tool = FunctionTool(uploaded_file_list)
index_file_tool = FunctionTool(index_uploaded_file)