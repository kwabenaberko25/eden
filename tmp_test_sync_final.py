import json
import uuid
import asyncio
import traceback
from sqlalchemy.orm import Mapped
from eden.app import Eden
from eden.db import Model, f

# 1. Define a Reactive Model
class SyncTask(Model):
    __reactive__ = True
    title: Mapped[str] = f(max_length=100)

# 2. Setup App
app = Eden()

async def debug_sync():
    print("--- Debugging Sync ---")
    try:
        from eden.realtime import manager
        from eden.db.base import after_insert
        
        # Check actual table name
        table_name = SyncTask.__table__.name
        print(f"SyncTask table name is: '{table_name}'")
        
        class MockWS:
            def __init__(self):
                self.sent = []
                self.client_state = None 
            async def send_text(self, data):
                self.sent.append(data)
            async def accept(self): 
                from starlette.websockets import WebSocketState
                self.client_state = WebSocketState.CONNECTED
            async def close(self): pass

        ws = MockWS()
        await ws.accept()
        await manager.connect(ws)
        
        # Subscribe using the ACTUAL table name
        print(f"Subscribing to '{table_name}'...")
        await manager.subscribe(ws, table_name)
        
        # Trigger insert
        task = SyncTask(id=uuid.uuid4(), title="Debug Prop")
        after_insert(None, None, task)
        
        # Wait for broadcast
        await asyncio.sleep(0.5)
        
        if ws.sent:
            print(f"✅ SUCCESS: Message received: {ws.sent[0]}")
        else:
            print("❌ FAILURE: No message received.")
            print(f"Current channels in manager: {manager.channels.keys()}")
            
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_sync())
