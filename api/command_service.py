from typing import Any, Dict, List, Optional

from loguru import logger
from open_notebook.database.job_queue import get_command_status, submit_command as sb_submit_command


class CommandService:
    """Generic service layer for command operations"""

    @staticmethod
    async def submit_command_job(
        module_name: str,  # Actually app_name for the job queue
        command_name: str,
        command_args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit a generic command job for background processing"""
        try:
            # Submit command to the Supabase-based job queue
            cmd_id = sb_submit_command(
                module_name,  # This is the app name (e.g., "open_notebook")
                command_name,  # Command name (e.g., "process_text")
                command_args,  # Input data
            )
            # Convert RecordID to string if needed
            if not cmd_id:
                raise ValueError("Failed to get cmd_id from submit_command")
            cmd_id_str = str(cmd_id)
            logger.info(
                f"Submitted command job: {cmd_id_str} for {module_name}.{command_name}"
            )
            return cmd_id_str

        except Exception as e:
            logger.error(f"Failed to submit command job: {e}")
            raise

    @staticmethod
    async def get_command_status(job_id: str) -> Dict[str, Any]:
        """Get status of any command job"""
        try:
            status = await get_command_status(job_id)
            return {
                "job_id": job_id,
                "status": status.status.value if status else "unknown",
                "result": status.result if status else None,
                "error_message": status.error_message if status else None,
                "created": status.created.isoformat() if hasattr(status, 'created') and status.created else None,
                "updated": status.updated.isoformat() if hasattr(status, 'updated') and status.updated else None,
                "progress": status.progress if status else None,
            }
        except Exception as e:
            logger.error(f"Failed to get command status: {e}")
            raise

    @staticmethod
    async def list_command_jobs(
        module_filter: Optional[str] = None,
        command_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List command jobs with optional filtering"""
        from open_notebook.database.job_queue import job_queue
        from open_notebook.database.job_queue import JobStatus
        # Convert string status filter to JobStatus enum if provided
        status_enum = None
        if status_filter:
            try:
                status_enum = JobStatus(status_filter)
            except ValueError:
                logger.warning(f"Invalid status filter: {status_filter}")
                
        jobs = await job_queue.list_jobs(
            app_name=module_filter,
            command_name=command_filter,
            status=status_enum,
            limit=limit
        )
        return jobs

    @staticmethod
    async def cancel_command_job(job_id: str) -> bool:
        """Cancel a running command job"""
        try:
            from open_notebook.database.job_queue import job_queue
            from open_notebook.database.job_queue import JobStatus
            # Update job status to cancelled
            await job_queue.update_job_status(job_id, JobStatus.CANCELLED, error_message="Job cancelled by user")
            logger.info(f"Cancelled job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel command job: {e}")
            raise
