import asyncio
import uuid
from sqlalchemy.orm import Mapped
from eden.db import Model, f
from eden.realtime import manager

# Enable reactive for this test model
class Task(Model):
    __reactive__ = True
    title: Mapped[str] = f(max_length=100)
    done: Mapped[bool] = f(default=False)

async def test_realtime_broadcast():
    print("--- Testing Real-time Broadcast ---")
    
    # Mock a websocket
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []
            self.client_state = None
        
        async def accept(self):
            from starlette.websockets import WebSocketState
            self.client_state = WebSocketState.CONNECTED
            
        async def send_text(self, message):
            self.sent_messages.append(message)
            
        async def disconnect(self):
            self.client_state = None

    ws = MockWebSocket()
    await manager.connect(ws)
    await manager.subscribe(ws, "tasks")
    
    # Create a task (this should trigger after_insert)
    # Note: In a real app, this happens inside a session. 
    # We'll trigger the listener manually or via a mock session if needed,
    # but let's see if the listener we attached to 'Model' works.
    
    from sqlalchemy import create_mock_engine
    from sqlalchemy.orm import sessionmaker
    
    task = Task(id=uuid.uuid4(), title="Test Realtime", done=False)
    
    print(f"Triggering insert for task: {task.title}")
    # Simulate what SQLAlchemy does
    from eden.db.base import after_insert
    after_insert(None, None, task)
    
    # Give it a tiny bit of time for the async task to run
    await asyncio.sleep(0.1)
    
    if ws.sent_messages:
        print(f"SUCCESS: Received {len(ws.sent_messages)} messages")
        for msg in ws.sent_messages:
            print(f"Message: {msg}")
    else:
        print("FAILURE: No messages received")

if __name__ == "__main__":
    asyncio.run(test_realtime_broadcast())
