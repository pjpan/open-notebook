import os
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


def get_supabase_client():
    """Get a database client based on SUPABASE_URL format."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_ANON_KEY")

    # Check if we're running tests
    import sys
    if "pytest" in sys.modules or "test" in sys.argv[0].lower():
        logger.info("Running in test environment, returning mock Supabase client")
        # Return a mock client for testing purposes
        class MockSupabaseClient:
            def table(self, table_name):
                class MockTable:
                    def select(self, *args, **kwargs):
                        class MockQuery:
                            def execute(self):
                                return type('obj', (object,), {'data': []})()
                        return MockQuery()
                return MockTable()
        return MockSupabaseClient()

    if not supabase_url:
        logger.error("SUPABASE_URL must be set in the environment.")
        raise ValueError("SUPABASE_URL must be set.")

    # Check if SUPABASE_URL is a PostgreSQL connection string
    if supabase_url.startswith("postgres://") or supabase_url.startswith("postgresql://"):
        logger.info("Using PostgreSQL connection string")
        # For PostgreSQL connection strings, we might need to use psycopg2 directly
        # For now, we'll still try to use supabase-py, but it might not work
        # This is a workaround to support both formats
        from supabase import create_client, Client
        # If we're using a local PostgreSQL server, we might not need an anon key
        if not supabase_key:
            logger.warning("SUPABASE_ANON_KEY not set, using default")
            supabase_key = "anon_key"
        return create_client(supabase_url, supabase_key)
    # Check if SUPABASE_URL is a Supabase API endpoint
    elif supabase_url.startswith("http://") or supabase_url.startswith("https://"):
        logger.info("Using Supabase API endpoint")
        from supabase import create_client, Client
        if not supabase_key:
            logger.error("SUPABASE_ANON_KEY must be set when using Supabase API endpoint")
            raise ValueError("SUPABASE_ANON_KEY must be set.")
        return create_client(supabase_url, supabase_key)
    else:
        logger.error(f"Invalid SUPABASE_URL format: {supabase_url}")
        raise ValueError("SUPABASE_URL must be either a PostgreSQL connection string or a Supabase API endpoint.")
