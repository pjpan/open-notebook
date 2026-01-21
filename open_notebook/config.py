import os
from supabase import create_client, Client
from loguru import logger

# ROOT DATA FOLDER
DATA_FOLDER = "./data"

# LANGGRAPH CHECKPOINT FILE
sqlite_folder = f"{DATA_FOLDER}/sqlite-db"
os.makedirs(sqlite_folder, exist_ok=True)
LANGGRAPH_CHECKPOINT_FILE = f"{sqlite_folder}/checkpoints.sqlite"

# UPLOADS FOLDER
UPLOADS_FOLDER = f"{DATA_FOLDER}/uploads"
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

# TIKTOKEN CACHE FOLDER
TIKTOKEN_CACHE_DIR = f"{DATA_FOLDER}/tiktoken-cache"
os.makedirs(TIKTOKEN_CACHE_DIR, exist_ok=True)


def get_supabase_client() -> Client:
    """Get a Supabase client."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_ANON_KEY must be set in the environment.")
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set.")

    return create_client(supabase_url, supabase_key)
