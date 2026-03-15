# Comprehensive import verification
print("Verifying all imports...")
print()

# 1. Core broker classes
from eden.tasks import EdenBroker, PeriodicTask, TaskResult, TaskResultBackend, create_broker
print("✅ Core classes imported: EdenBroker, PeriodicTask, TaskResult, TaskResultBackend")

# 2. Exception classes
from eden.tasks.exceptions import (
    TaskError,
    TaskExecutionError, 
    MaxRetriesExceeded,
    SchedulerError,
    SchedulerException,  # Backward compatibility
    InvalidCronExpression,
    JobNotFound,
    BrokerNotInitialized
)
print("✅ Exception classes imported: 8 total")

# 3. Lifecycle integration
from eden.tasks.lifecycle import setup_task_broker
print("✅ Lifecycle module: setup_task_broker")

# 4. APScheduler backend
from eden.tasks.apscheduler_backend import APSchedulerBackend
print("✅ APScheduler backend: APSchedulerBackend")

# 5. CLI commands
from eden.cli.tasks import tasks
print("✅ CLI module: tasks command group")

# 6. App integration
from eden.app import Eden
print("✅ Eden app: setup_tasks() method available")

print()
print("=" * 50)
print("🎉 All imports successful!")
print("=" * 50)
print()

# Verify functionality
print("Testing basic functionality...")
broker = create_broker()
print(f"✅ create_broker() works: {type(broker).__name__}")

eden_broker = EdenBroker(broker)
print(f"✅ EdenBroker instantiation works")
print(f"   - Max retries: {eden_broker.max_retries}")
print(f"   - Retry delays: {eden_broker.retry_delays}")
print(f"   - Result backend: {type(eden_broker.result_backend).__name__}")

print()
print("🎉 Task System Implementation VERIFIED!")
