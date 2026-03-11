import asyncio
import uuid
import json
from starlette.testclient import TestClient
from sqlalchemy.orm import Mapped
from eden.app import Eden
from eden.db import Model, f
from eden.realtime import manager

# 1. Define a Reactive Model for testing
class LiveTask(Model):
    __reactive__ = True
    title: Mapped[str] = f(max_length=100)

# 2. Setup the Eden App
app = Eden()

async def run_integration_test():
    print("--- Starting Integration Test: Real-time Sync ---")
    
    # We use TestClient as a context manager to trigger lifespan events if any
    with TestClient(app) as client:
        # 3. Connect to the WebSocket
        print("Connecting to /_eden/sync...")
        # Starlette TestClient.websocket_connect is a context manager
        with client.websocket_connect("/_eden/sync") as websocket:
            # 4. Subscribe to the 'livetasks' channel
            # Note: Model table name is usually lowercase plural by default in many ORMs, 
            # let's check what Eden uses. Default is usually class name lowercase + 's'.
            channel = "livetasks"
            print(f"Subscribing to '{channel}'...")
            websocket.send_json({"action": "subscribe", "channel": channel})
            
            # 5. Trigger an ORM event manually
            print("Triggering ORM event...")
            task = LiveTask(id=uuid.uuid4(), title="Integrated Verification")
            
            # In a real app, this is triggered by SQLAlchemy event listeners we added.
            # We import the listener to manually trigger it for the test.
            from eden.db.base import after_insert
            
            # Triggering the event
            after_insert(None, None, task)
            
            # 6. Receive the broadcast
            print("Waiting for broadcast...")
            try:
                # websocket.receive_json() is blocking in TestClient
                data = websocket.receive_json()
                print(f"Received Message: {json.dumps(data, indent=2)}")
                
                if data.get("event") == f"{channel}:created":
                    print("✅ SUCCESS: Received correct model event!")
                    return True
                else:
                    print(f"❌ FAILURE: Unexpected message: {data}")
                    return False
            except Exception as e:
                print(f"❌ FAILURE: Did not receive message. Error: {e}")
                return False

if __name__ == "__main__":
    # TestClient's websocket_connect is synchronous, so we run this in a simple script.
    # However, since manager uses asyncio.create_task, we might need to be careful.
    # But in TestClient, the "app" runs in a way that often handles this.
    success = asyncio.run(run_integration_test())
    if not success:
        exit(1)
