from open_notebook.config import get_supabase_client
from contextlib import contextmanager
from loguru import logger
from typing import Any, Dict, List, Optional

supabase_client = get_supabase_client()

async def repo_query(table: str, select: str = "*", filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute a SELECT query and return the results"""
    try:
        query = supabase_client.table(table).select(select)
        if filters:
            for key, value in filters.items():
                if isinstance(value, str) and value.startswith("ilike."):
                    # Handle ilike operator for partial matching
                    pattern = value[6:]  # Remove "ilike." prefix
                    query = query.ilike(key, pattern)
                else:
                    query = query.eq(key, value)
        result = query.execute()
        return result.data
    except Exception as e:
        logger.exception(e)
        raise

async def repo_create(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new record in the specified table"""
    try:
        result = supabase_client.table(table).insert(data).execute()
        return result.data[0] if result.data else {}
    except Exception as e:
        logger.exception(e)
        raise RuntimeError("Failed to create record")

async def repo_update(table: str, id: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Update an existing record by table and id"""
    try:
        result = supabase_client.table(table).update(data).eq("id", id).execute()
        return result.data
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to update record: {str(e)}")


async def repo_update_int_id(table: str, id: int, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Update an existing record by table and integer id"""
    try:
        result = supabase_client.table(table).update(data).eq("id", id).execute()
        return result.data
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to update record: {str(e)}")


async def repo_upsert(table: str, id_column: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Upsert a record in the specified table"""
    try:
        result = supabase_client.table(table).upsert(data, on_conflict=id_column).execute()
        return result.data
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to upsert record: {str(e)}")

async def repo_delete(table: str, id: str):
    """Delete a record by record id"""
    try:
        result = supabase_client.table(table).delete().eq("id", id).execute()
        return result.data
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to delete record: {str(e)}")


async def repo_delete_int_id(table: str, id: int):
    """Delete a record by integer id"""
    try:
        result = supabase_client.table(table).delete().eq("id", id).execute()
        return result.data
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to delete record: {str(e)}")

async def repo_relate(
    from_table: str,
    from_id: str,
    relationship: str,
    to_table: str,
    to_id: str,
    data: Optional[Dict[str, Any]] = None,
):
    """Create a relationship between two records with optional data"""
    join_table = f"{from_table}_{to_table}_{relationship}"
    relation_data = {
        f"{from_table}_id": from_id,
        f"{to_table}_id": to_id,
    }
    if data:
        relation_data.update(data)
    
    try:
        result = supabase_client.table(join_table).insert(relation_data).execute()
        return result.data
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to create relationship: {str(e)}")


async def repo_relate_int_ids(
    from_table: str,
    from_id: int,
    relationship: str,
    to_table: str,
    to_id: int,
    data: Optional[Dict[str, Any]] = None,
):
    """Create a relationship between two records with integer IDs"""
    join_table = f"{from_table}_{to_table}_{relationship}"
    relation_data = {
        f"{from_table}_id": from_id,
        f"{to_table}_id": to_id,
    }
    if data:
        relation_data.update(data)
    
    try:
        result = supabase_client.table(join_table).insert(relation_data).execute()
        return result.data
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to create relationship: {str(e)}")

async def repo_unrelate(
    from_table: str,
    from_id: str,
    relationship: str,
    to_table: str,
    to_id: str,
):
    """Delete a relationship between two records"""
    join_table = f"{from_table}_{to_table}_{relationship}"
    try:
        result = supabase_client.table(join_table).delete().eq(f"{from_table}_id", from_id).eq(f"{to_table}_id", to_id).execute()
        return result.data
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to delete relationship: {str(e)}")


async def repo_unrelate_int_ids(
    from_table: str,
    from_id: int,
    relationship: str,
    to_table: str,
    to_id: int,
):
    """Delete a relationship between two records with integer IDs"""
    join_table = f"{from_table}_{to_table}_{relationship}"
    try:
        result = supabase_client.table(join_table).delete().eq(f"{from_table}_id", from_id).eq(f"{to_table}_id", to_id).execute()
        return result.data
    except Exception as e:
        logger.exception(e)
        raise RuntimeError(f"Failed to delete relationship: {str(e)}")

async def repo_count(table: str, filters: Optional[Dict[str, Any]] = None) -> int:
    """Execute a COUNT query and return the result"""
    try:
        query = supabase_client.table(table).select("id", count='exact')
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        result = query.execute()
        return result.count or 0
    except Exception as e:
        logger.exception(e)
        raise

async def repo_vector_search(table: str, column: str, query_embedding: List[float], 
                           similarity_threshold: float = 0.5, limit: int = 10) -> List[Dict[str, Any]]:
    """Perform vector similarity search using Supabase's pgvector functionality"""
    try:
        # For now, this is a simplified approach - in real implementation you'd want
        # to create a custom RPC function in Supabase such as:
        # CREATE FUNCTION match_documents(query_embedding vector(1536), similarity_threshold float, match_count int)
        # AS $$ SELECT * FROM table ORDER BY embedding <=> query_embedding LIMIT match_count; $$
        
        # For now, we'll return an empty list indicating vector search isn't fully implemented yet
        # This would require setting up the proper pgvector functions in Supabase
        return []
    except Exception as e:
        logger.exception(f"Vector search failed: {e}")
        # Fallback to regular search if vector search is not available
        return []
