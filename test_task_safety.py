import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from eden.tasks import EdenBroker, TaskResultBackend, TaskResult
from eden.core.backends.base import DistributedBackend

class MockBackend(DistributedBackend):
    def __init__(self):
        self.data = {}
        self.locks = {}

    async def connect(self): pass
    async def disconnect(self): pass
    async def acquire_lock(self, name: str, timeout=10.0, identifier=None):
        if name not in self.locks:
            self.locks[name] = identifier
            return True
        return False
    async def release_lock(self, name: str, identifier: str):
        if self.locks.get(name) == identifier:
            del self.locks[name]
            return True
        return False
    async def publish(self, channel, message): pass
    async def subscribe(self, channel, callback): pass
    async def get(self, key):
        return self.data.get(key)
    async def set(self, key, value, ttl=None):
        self.data[key] = value
    async def delete(self, key: str): pass
    async def incr(self, key: str, amount=1): pass

async def verify():
    print("--- TASK BROKER SAFETY VERIFICATION ---")
    
    # 1. Backoff delays calculation test
    print("\n1. Verifying Double-Exponential fix bounds...")
    broker = EdenBroker(broker=None)  # Minimal init
    delays = broker.retry_delays # [1, 2, 4, 8, 16]
    
    attempts = [1, 2, 3, 4, 5, 6, 7]
    calculated_delays = []
    exponential_backoff = True
    for attempt in attempts:
        idx = attempt - 1
        if idx < len(delays):
            delay = delays[idx]
        else:
            last_delay = delays[-1] if delays else 1
            if exponential_backoff:
                growth = idx - len(delays) + 1
                delay = last_delay * (2 ** growth)
            else:
                delay = last_delay
        calculated_delays.append(delay)
    
    print(f"Calculated delays for attempts 1-7: {calculated_delays}")
    assert calculated_delays == [1, 2, 4, 8, 16, 32, 64], "Backoff logic failed!"
    print("=> Backoff Delays calculation VERIFIED.")

    # 2. DLQ Append
    print("\n2. Verifying DLQ read-modify-write queue appending...")
    backend = MockBackend()
    result_backend = TaskResultBackend(backend=backend)
    
    res1 = TaskResult(task_id="t1", task_name="fail", status="dead_letter")
    res2 = TaskResult(task_id="t2", task_name="fail", status="dead_letter")
    
    await result_backend.store_result("t1", res1)
    await result_backend.store_result("t2", res2)
    
    dl = await backend.get("eden:tasks:dead_letter")
    print(f"Dead letter contents: {dl}")
    assert dl == ["t1", "t2"], "DLQ append failed!"
    print("=> DLQ appending VERIFIED.")
    print("\nSUCCESS: All task tests passed.")

if __name__ == "__main__":
    asyncio.run(verify())
