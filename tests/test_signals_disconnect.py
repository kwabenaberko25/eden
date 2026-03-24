import pytest
import weakref
from eden.db.signals import Signal

@pytest.mark.asyncio
async def test_signals_disconnect_basic():
    """Verifies that Signal.disconnect works properly."""
    sig = Signal("test")
    received = []
    
    def handler(sender, instance, **kwargs):
        received.append(kwargs.get("val"))
        
    # 1. Connect
    sig.connect(handler)
    await sig.send(sender=None, instance=None, val=1)
    assert received == [1]
    
    # 2. Disconnect
    sig.disconnect(handler)
    await sig.send(sender=None, instance=None, val=2)
    assert received == [1] # Should not change

@pytest.mark.asyncio
async def test_signals_disconnect_with_dispatch_uid():
    """Verifies that Signal.disconnect works with dispatch_uid."""
    sig = Signal("test")
    received = []
    
    def handler(sender, instance, **kwargs):
        received.append(kwargs.get("val"))
        
    sig.connect(handler, dispatch_uid="my_unique_id")
    await sig.send(sender=None, instance=None, val=1)
    assert received == [1]
    
    sig.disconnect(dispatch_uid="my_unique_id")
    await sig.send(sender=None, instance=None, val=2)
    assert received == [1]

@pytest.mark.asyncio
async def test_signals_disconnect_with_sender():
    """Verifies that Signal.disconnect respects sender filter."""
    sig = Signal("test")
    received = []
    
    class Sender: pass
    s1 = Sender()
    s2 = Sender()
    
    def handler(sender, instance, **kwargs):
        received.append(kwargs.get("val"))
        
    sig.connect(handler, sender=s1)
    
    # Trigger with filtered sender
    await sig.send(sender=s1, instance=None, val=1)
    assert received == [1]
    
    # Trigger with different sender (should NOT reach handler)
    await sig.send(sender=s2, instance=None, val=2)
    assert received == [1]
    
    # Disconnect for s1
    sig.disconnect(handler, sender=s1)
    await sig.send(sender=s1, instance=None, val=3)
    assert received == [1]
