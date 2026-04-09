"""
Eden Framework — APScheduler Database Persistence

Persistent job storage with execution history and retry tracking.

**Features:**
- Job persistence across restarts
- Execution history and logs
- Failure tracking and retry logic
- Performance metrics per job

**Usage:**

    from eden.scheduler_db import DatabaseJobStore
    from eden.db import SessionLocal
    
    job_store = DatabaseJobStore(session_factory=SessionLocal)
    scheduler = APSchedulerBackend(config=config, job_store=job_store)
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================================================
# Database Models
# ============================================================================

class JobModel(Base):
    """Scheduled job database model."""
    __tablename__ = "scheduled_jobs"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    func_name = Column(String(255), nullable=False)
    trigger = Column(String(50), nullable=False)  # interval, cron, date
    trigger_params = Column(JSON, nullable=True)
    args = Column(JSON, nullable=True)
    kwargs = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True)
    next_run_time = Column(DateTime, nullable=True)
    last_run_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String(255), nullable=True)


class JobExecutionModel(Base):
    """Job execution history."""
    __tablename__ = "job_executions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False)
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)  # pending, running, success, failed, skipped
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    output = Column(Text, nullable=True)


class JobMetricsModel(Base):
    """Job performance metrics."""
    __tablename__ = "job_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False)
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    skipped_executions = Column(Integer, default=0)
    total_duration_seconds = Column(Float, default=0.0)
    average_duration_seconds = Column(Float, default=0.0)
    last_success = Column(DateTime, nullable=True)
    last_failure = Column(DateTime, nullable=True)


# ============================================================================
# Database Job Store
# ============================================================================

class DatabaseJobStore:
    """Database backend for job persistence."""
    
    def __init__(self, session_factory):
        """
        Initialize database job store.
        
        Args:
            session_factory: SQLAlchemy session factory
        """
        self.session_factory = session_factory
    
    def _get_session(self) -> Session:
        """Get database session."""
        return self.session_factory()
    
    # ========================================================================
    # Job Operations
    # ========================================================================
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID."""
        session = self._get_session()
        try:
            job = session.query(JobModel).filter_by(id=job_id).first()
            if job:
                return self._job_to_dict(job)
            return None
        finally:
            session.close()
    
    async def get_all_jobs(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """Get all jobs."""
        session = self._get_session()
        try:
            query = session.query(JobModel)
            if enabled_only:
                query = query.filter_by(enabled=True)
            
            jobs = query.all()
            return [self._job_to_dict(j) for j in jobs]
        finally:
            session.close()
    
    async def save_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """Save a job."""
        session = self._get_session()
        try:
            existing = session.query(JobModel).filter_by(id=job_id).first()
            
            if existing:
                # Update
                for key, value in job_data.items():
                    if hasattr(existing, key) and key != "id":
                        setattr(existing, key, value)
                existing.updated_at = datetime.now()
            else:
                # Create
                job_data["id"] = job_id
                job_data["created_at"] = datetime.now()
                job_data["updated_at"] = datetime.now()
                
                new_job = JobModel(**job_data)
                session.add(new_job)
            
            session.commit()
            logger.info(f"Job saved: {job_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving job: {e}")
            return False
        finally:
            session.close()
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        session = self._get_session()
        try:
            job = session.query(JobModel).filter_by(id=job_id).first()
            
            if not job:
                return False
            
            session.delete(job)
            session.commit()
            
            logger.info(f"Job deleted: {job_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting job: {e}")
            return False
        finally:
            session.close()
    
    async def update_next_run(self, job_id: str, next_run_time: Optional[datetime]) -> bool:
        """Update next run time."""
        session = self._get_session()
        try:
            job = session.query(JobModel).filter_by(id=job_id).first()
            
            if not job:
                return False
            
            job.next_run_time = next_run_time
            job.updated_at = datetime.now()
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating next run: {e}")
            return False
        finally:
            session.close()
    
    # ========================================================================
    # Execution Operations
    # ========================================================================
    
    async def log_execution(
        self, job_id: str, status: str, duration_seconds: float = None,
        error_message: str = None, output: str = None
    ) -> bool:
        """Log a job execution."""
        session = self._get_session()
        try:
            execution = JobExecutionModel(
                job_id=job_id,
                status=status,
                duration_seconds=duration_seconds,
                error_message=error_message,
                output=output,
                completed_at=datetime.now() if status != "running" else None,
            )
            session.add(execution)
            
            # Update job's last_run_time
            job = session.query(JobModel).filter_by(id=job_id).first()
            if job:
                job.last_run_time = datetime.now()
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging execution: {e}")
            return False
        finally:
            session.close()
    
    async def get_execution_history(
        self, job_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get execution history for a job."""
        session = self._get_session()
        try:
            executions = session.query(JobExecutionModel)\
                .filter_by(job_id=job_id)\
                .order_by(JobExecutionModel.started_at.desc())\
                .limit(limit)\
                .offset(offset)\
                .all()
            
            return [self._execution_to_dict(e) for e in executions]
        finally:
            session.close()
    
    async def get_recent_failures(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent job failures."""
        session = self._get_session()
        try:
            failures = session.query(JobExecutionModel)\
                .filter_by(status="failed")\
                .order_by(JobExecutionModel.started_at.desc())\
                .limit(limit)\
                .all()
            
            return [self._execution_to_dict(e) for e in failures]
        finally:
            session.close()
    
    # ========================================================================
    # Metrics Operations
    # ========================================================================
    
    async def get_metrics(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a job."""
        session = self._get_session()
        try:
            metrics = session.query(JobMetricsModel).filter_by(job_id=job_id).first()
            
            if metrics:
                return self._metrics_to_dict(metrics)
            
            # Create default metrics
            metrics = JobMetricsModel(job_id=job_id)
            session.add(metrics)
            session.commit()
            
            return self._metrics_to_dict(metrics)
        finally:
            session.close()
    
    async def update_metrics(self, job_id: str, status: str, duration_seconds: float = None):
        """Update metrics for a job execution."""
        session = self._get_session()
        try:
            metrics = session.query(JobMetricsModel).filter_by(job_id=job_id).first()
            
            if not metrics:
                metrics = JobMetricsModel(job_id=job_id)
                session.add(metrics)
            
            metrics.total_executions += 1
            
            if status == "success":
                metrics.successful_executions += 1
                metrics.last_success = datetime.now()
            elif status == "failed":
                metrics.failed_executions += 1
                metrics.last_failure = datetime.now()
            elif status == "skipped":
                metrics.skipped_executions += 1
            
            if duration_seconds:
                metrics.total_duration_seconds += duration_seconds
                metrics.average_duration_seconds = \
                    metrics.total_duration_seconds / metrics.total_executions
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating metrics: {e}")
            return False
        finally:
            session.close()
    
    async def get_all_metrics(self) -> List[Dict[str, Any]]:
        """Get metrics for all jobs."""
        session = self._get_session()
        try:
            metrics = session.query(JobMetricsModel).all()
            return [self._metrics_to_dict(m) for m in metrics]
        finally:
            session.close()
    
    # ========================================================================
    # Internal Methods
    # ========================================================================
    
    def _job_to_dict(self, job: JobModel) -> Dict[str, Any]:
        """Convert job model to dict."""
        return {
            "id": job.id,
            "name": job.name,
            "description": job.description,
            "func_name": job.func_name,
            "trigger": job.trigger,
            "trigger_params": job.trigger_params,
            "args": job.args,
            "kwargs": job.kwargs,
            "enabled": job.enabled,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "last_run_time": job.last_run_time.isoformat() if job.last_run_time else None,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "created_by": job.created_by,
        }
    
    def _execution_to_dict(self, execution: JobExecutionModel) -> Dict[str, Any]:
        """Convert execution model to dict."""
        return {
            "id": execution.id,
            "job_id": execution.job_id,
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "status": execution.status,
            "duration_seconds": execution.duration_seconds,
            "error_message": execution.error_message,
            "retry_count": execution.retry_count,
            "output": execution.output,
        }
    
    def _metrics_to_dict(self, metrics: JobMetricsModel) -> Dict[str, Any]:
        """Convert metrics model to dict."""
        return {
            "job_id": metrics.job_id,
            "total_executions": metrics.total_executions,
            "successful_executions": metrics.successful_executions,
            "failed_executions": metrics.failed_executions,
            "skipped_executions": metrics.skipped_executions,
            "success_rate": (metrics.successful_executions / metrics.total_executions * 100)
                if metrics.total_executions > 0 else 0,
            "total_duration_seconds": metrics.total_duration_seconds,
            "average_duration_seconds": metrics.average_duration_seconds,
            "last_success": metrics.last_success.isoformat() if metrics.last_success else None,
            "last_failure": metrics.last_failure.isoformat() if metrics.last_failure else None,
        }
