import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from eden.tasks import EdenBroker, InMemoryBroker
from eden.context import context_manager

# Setup broker
broker = EdenBroker(InMemoryBroker())

# Mock kicked task
class MockKicked:
    def __init__(self, task_id):
        self.task_id = task_id

@broker.task()
def dummy_periodic_payload():
    return "periodic-job-payload"

# Since InMemoryBroker doesn't mock kiq nicely enough for asyncio sleeping properly outside this loop, 
# let's just intercept the kiq function for the scope of the test.
original_kiq = dummy_periodic_payload.kiq

async def fake_kiq(*args, **kwargs):
    # This represents exactly what the background worker would pull from context!
    snap = context_manager.get_context_snapshot()
    captured_req_id = context_manager.get_request_id()
    
    print(f"Inside fake kiq - worker side captured correlation ID from Context: {captured_req_id}")
    return MockKicked("queue-generated-uuid-5555")

dummy_periodic_payload.kiq = fake_kiq

async def test_run():
    print("--- TESTING TASK TRACKING UNIFICATION ---")
    
    # We will trigger the periodic task schedule manually without spinning the while True
    from eden.tasks import PeriodicTask
    ptask = PeriodicTask(dummy_periodic_payload, broker, seconds=10)
    
    # We'll cancel the task immediately after it starts to run one loop pass.
    # We monkeypatch the sleep so that the first sleep (which is interval wait) is bypassed by setting interval to 0,
    # or we can just mock sleep to raise BreakLoop AFTER 1 execution.
    class BreakLoop(Exception): pass
    original_sleep = asyncio.sleep
    sleep_count = 0
    async def mock_sleep(d):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count > 1:
            raise BreakLoop()
        return await original_sleep(0)
    asyncio.sleep = mock_sleep
    
    try:
        await ptask._run_loop()
    except BreakLoop:
        pass
    finally:
        asyncio.sleep = original_sleep
        
    print("\nValidating Scheduler Log Storage...")
    results = await broker._result_backend.get_all_results()
    assert len(results) == 1
    stored = results[0]
    
    print(f"Stored periodic dispatch log ID: {stored.task_id}")
    print(f"Stored periodic dispatch properties: status='{stored.status}', status_message='{stored.status_message}'")
    print(f"Stored metadata dictionary: {stored.metadata}")
    
    assert stored.task_id.startswith("periodic-dummy_periodic_payload-")
    assert "queue-generated-uuid-5555" in stored.status_message
    assert stored.metadata["broker_task_id"] == "queue-generated-uuid-5555"
    
    print("=> Validation Complete! Scheduler record matches Queue Execution.")

if __name__ == "__main__":
    asyncio.run(test_run())
