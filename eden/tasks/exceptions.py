"""
Eden Tasks — Custom Exceptions

Provides exceptions for task execution, retry, and scheduling failures.
"""


class TaskError(Exception):
    """Base exception for all task-related errors."""

    pass


class TaskExecutionError(TaskError):
    """Raised when a task fails during execution."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
        original_exception: Exception | None = None,
        retry_count: int = 0,
    ) -> None:
        """
        Initialize task execution error.

        Args:
            message: Human-readable error message
            task_id: ID of the task that failed
            original_exception: The underlying exception that caused the failure
            retry_count: Number of retries attempted so far
        """
        super().__init__(message)
        self.task_id = task_id
        self.original_exception = original_exception
        self.retry_count = retry_count


class MaxRetriesExceeded(TaskError):
    """Raised when a task exhausts all retry attempts."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
        max_retries: int = 0,
        last_error: Exception | None = None,
    ) -> None:
        """
        Initialize max retries exceeded error.

        Args:
            message: Human-readable error message
            task_id: ID of the task that failed
            max_retries: Maximum number of retries allowed
            last_error: The error from the final attempt
        """
        super().__init__(message)
        self.task_id = task_id
        self.max_retries = max_retries
        self.last_error = last_error


class SchedulerError(TaskError):
    """Raised when scheduler operations fail."""

    pass


class InvalidCronExpression(SchedulerError):
    """Raised when a cron expression is invalid."""

    def __init__(self, expression: str, reason: str) -> None:
        """
        Initialize invalid cron expression error.

        Args:
            expression: The invalid cron expression
            reason: Explanation of what's invalid
        """
        super().__init__(f"Invalid cron expression '{expression}': {reason}")
        self.expression = expression
        self.reason = reason


class JobNotFound(SchedulerError):
    """Raised when a scheduled job cannot be found."""

    def __init__(self, job_id: str) -> None:
        """
        Initialize job not found error.

        Args:
            job_id: ID of the job that was not found
        """
        super().__init__(f"Scheduled job '{job_id}' not found")
        self.job_id = job_id


class BrokerNotInitialized(TaskError):
    """Raised when broker operations are attempted before startup."""

    pass


# Backward compatibility alias for old test suite
SchedulerException = SchedulerError
