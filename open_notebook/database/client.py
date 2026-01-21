from open_notebook.config import get_supabase_client

def get_db():
    """FastAPI dependency to get a Supabase client."""
    return get_supabase_client()
