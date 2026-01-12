import os
from pathlib import Path
from google import genai

CONFIG_PATH = Path(__file__).parent.parent / 'file_store_config.json'
STORE_NAME = os.getenv('STORE_NAME')

api_key = os.getenv('FILE_SEARCH_API_KEY') or os.getenv('GOOGLE_API_KEY')
client = genai.Client(api_key=api_key)
