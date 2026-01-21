"""Supabase-based job queue implementation"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from supabase import create_client, Client
from loguru import logger
import asyncio
import json


class JobStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobResult:
    def __init__(self, status: JobStatus, result: Optional[Any] = None, 
                 error_message: Optional[str] = None, progress: Optional[float] = None):
        self.status = status
        self.result = result
        self.error_message = error_message
        self.progress = progress
        self.created = datetime.now()
        self.updated = datetime.now()


class SupabaseJobQueue:
    """Job queue implementation using Supabase"""
    
    def __init__(self):
        from open_notebook.config import get_supabase_client
        self.client: Client = get_supabase_client()
        self.job_table = "jobs"
    
    async def submit_job(self, app_name: str, command_name: str, args: Dict[str, Any]) -> str:
        """Submit a job to the queue"""
        job_id = str(uuid.uuid4())
        
        job_data = {
            "id": job_id,
            "app_name": app_name,
            "command_name": command_name,
            "args": json.dumps(args),
            "status": JobStatus.PENDING.value,
            "progress": 0.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        try:
            result = self.client.table(self.job_table).insert(job_data).execute()
            logger.info(f"Job submitted: {job_id} for {app_name}.{command_name}")
            return job_id
        except Exception as e:
            logger.error(f"Failed to submit job: {e}")
            raise
    
    async def get_job_status(self, job_id: str) -> JobResult:
        """Get the status of a job"""
        try:
            result = self.client.table(self.job_table).select("*").eq("id", job_id).execute()
            
            if not result.data:
                return JobResult(JobStatus.FAILED, error_message="Job not found")
            
            job = result.data[0]
            status = JobStatus(job.get('status', 'unknown'))
            
            return JobResult(
                status=status,
                result=json.loads(job.get('result')) if job.get('result') else None,
                error_message=job.get('error_message'),
                progress=job.get('progress', 0.0)
            )
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return JobResult(JobStatus.FAILED, error_message=str(e))
    
    async def update_job_status(self, job_id: str, status: JobStatus, 
                               result: Optional[Any] = None, error_message: Optional[str] = None,
                               progress: Optional[float] = None):
        """Update the status of a job"""
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.now().isoformat(),
            }
            
            if result is not None:
                update_data["result"] = json.dumps(result)
            if error_message is not None:
                update_data["error_message"] = error_message
            if progress is not None:
                update_data["progress"] = progress
            
            self.client.table(self.job_table).update(update_data).eq("id", job_id).execute()
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
    
    async def list_jobs(self, app_name: Optional[str] = None, 
                        command_name: Optional[str] = None,
                        status: Optional[JobStatus] = None,
                        limit: int = 50) -> List[Dict[str, Any]]:
        """List jobs with optional filters"""
        try:
            query = self.client.table(self.job_table).select("*").order("created_at", desc=True).limit(limit)
            
            if app_name:
                query = query.eq("app_name", app_name)
            if command_name:
                query = query.eq("command_name", command_name)
            if status:
                query = query.eq("status", status.value)
            
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []


# Global job queue instance
job_queue = SupabaseJobQueue()


async def get_command_status(job_id: str) -> JobResult:
    """Wrapper function to get command status"""
    return await job_queue.get_job_status(job_id)


def submit_command(app_name: str, command_name: str, args: Dict[str, Any]) -> str:
    """Wrapper function to submit command"""
    import asyncio
    
    async def _submit():
        return await job_queue.submit_job(app_name, command_name, args)
    
    # This is a synchronous wrapper for the async function
    # In a real implementation, you might want to handle this differently
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_submit())
    finally:
        loop.close()