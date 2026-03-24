"""
Tests for Signal system fixes (Issue #2 from analysis).

Verifies:
1. disconnect() works correctly with named functions
2. disconnect() works correctly with lambda/closure receivers  
3. Lambda receivers connected with weak=True are NOT garbage collected
4. dispatch_uid based disconnect works
5. Sender filtering works correctly
"""

import pytest
import gc
from eden.db.signals import Signal


def test_signal_connect_and_disconnect_named_function():
    """Named function receivers can be connected and disconnected by reference."""
    sig = Signal("test")
    calls = []

    def my_receiver(**kwargs):
        calls.append(kwargs)

    sig.connect(my_receiver, weak=False)
    assert len(sig._live_receivers) == 1

    result = sig.disconnect(my_receiver)
    assert result is True
    assert len(sig._live_receivers) == 0


def test_signal_disconnect_by_dispatch_uid():
    """Receivers can be disconnected by dispatch_uid."""
    sig = Signal("test")

    def my_receiver(**kwargs):
        pass

    sig.connect(my_receiver, dispatch_uid="unique_1", weak=False)
    assert len(sig._live_receivers) == 1

    result = sig.disconnect(dispatch_uid="unique_1")
    assert result is True
    assert len(sig._live_receivers) == 0


def test_signal_lambda_not_garbage_collected():
    """Lambda receivers should not be garbage collected when connected."""
    sig = Signal("test")
    
    # Connect a lambda — with the old code, this would be GC'd immediately
    sig.connect(lambda **kw: None, weak=True)
    
    # Force GC
    gc.collect()
    
    # The receiver should still be alive 
    assert len(sig._live_receivers) == 1
    
    # Resolve it — should NOT be None
    _, r_ref, _, _ = sig._live_receivers[0]
    receiver = sig._resolve_ref(r_ref)
    assert receiver is not None


@pytest.mark.asyncio
async def test_signal_send_receives_correctly():
    """Connected receivers receive signal sends."""
    sig = Signal("test")
    calls = []

    async def my_receiver(**kwargs):
        calls.append(kwargs.get("instance"))

    sig.connect(my_receiver, weak=False)
    await sig.send(sender=None, instance="hello")
    
    assert len(calls) == 1
    assert calls[0] == "hello"


@pytest.mark.asyncio
async def test_signal_disconnect_then_send():
    """After disconnect, receiver should NOT receive sends."""
    sig = Signal("test")
    calls = []

    async def my_receiver(**kwargs):
        calls.append(1)

    sig.connect(my_receiver, weak=False)
    await sig.send(sender=None, instance="test")
    assert len(calls) == 1

    sig.disconnect(my_receiver)
    await sig.send(sender=None, instance="test2")
    assert len(calls) == 1  # Still 1, not 2


@pytest.mark.asyncio
async def test_signal_sender_filtering():
    """Receivers with sender filters only fire for the correct sender."""
    sig = Signal("test")
    calls = []

    class ModelA:
        pass

    class ModelB:
        pass

    async def my_receiver(**kwargs):
        calls.append(kwargs.get("sender"))

    sig.connect(my_receiver, sender=ModelA, weak=False)
    
    await sig.send(sender=ModelA, instance="a")
    assert len(calls) == 1
    assert calls[0] is ModelA

    await sig.send(sender=ModelB, instance="b")
    assert len(calls) == 1  # Didn't fire for ModelB


def test_signal_dispatch_uid_replaces():
    """Connecting with the same dispatch_uid replaces the previous receiver."""
    sig = Signal("test")

    def receiver_1(**kwargs):
        pass

    def receiver_2(**kwargs):
        pass

    sig.connect(receiver_1, dispatch_uid="same_uid", weak=False)
    assert len(sig._live_receivers) == 1

    sig.connect(receiver_2, dispatch_uid="same_uid", weak=False)
    assert len(sig._live_receivers) == 1  # Still 1, replaced

    # The stored receiver should be receiver_2
    _, r_ref, _, _ = sig._live_receivers[0]
    assert sig._resolve_ref(r_ref) is receiver_2
