
from __future__ import annotations
import asyncio
import inspect
import weakref
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
import logging

logger = logging.getLogger("eden.db.signals")

T = TypeVar("T")

class Signal:
    """
    A decoupled signal system for Eden models.
    Supports both sync and async receivers.
    """

    def __init__(self, name: str):
        self.name = name
        self._receivers: List[weakref.KeyedRef] = []
        # Use a list of tuples: (receiver_ref, sender_id, dispatch_uid)
        self._live_receivers: List[tuple] = []

    def connect(
        self,
        receiver: Callable,
        sender: Optional[Type[Any]] = None,
        weak: bool = True,
        dispatch_uid: Optional[str] = None,
    ) -> None:
        """
        Connect a receiver to this signal.

        Args:
            receiver: The callable to be notified.
            sender: Optional specific sender (Model class) to filter by.
            weak: Whether to use a weak reference to the receiver.
            dispatch_uid: A unique identifier for the receiver to prevent duplicates.
        """
        if dispatch_uid:
            # Check for existing receiver with same dispatch_uid
            for i, (r, s, uid) in enumerate(self._live_receivers):
                if uid == dispatch_uid:
                    self._live_receivers[i] = (
                        self._make_id(receiver, weak),
                        self._make_id(sender, True) if sender else None,
                        dispatch_uid,
                    )
                    return

        self._live_receivers.append(
            (
                self._make_id(receiver, weak),
                self._make_id(sender, True) if sender else None,
                dispatch_uid,
            )
        )

    def disconnect(
        self,
        receiver: Optional[Callable] = None,
        sender: Optional[Type[Any]] = None,
        dispatch_uid: Optional[str] = None,
    ) -> bool:
        """Disconnect a receiver from this signal."""
        disconnected = False
        to_remove = []

        for i, (r_id, s_id, uid) in enumerate(self._live_receivers):
            if dispatch_uid and uid == dispatch_uid:
                to_remove.append(i)
                disconnected = True
                continue
            
            if receiver and self._make_id(receiver, False) == r_id:
                if sender is None or self._make_id(sender, True) == s_id:
                    to_remove.append(i)
                    disconnected = True
        
        for i in reversed(to_remove):
            self._live_receivers.pop(i)
            
        return disconnected

    async def send(self, sender: Type[Any], instance: Any, **kwargs: Any) -> List[tuple[Callable, Any]]:
        """
        Notify all connected receivers.
        Returns a list of (receiver, response) tuples.
        """
        responses = []
        sender_id = self._make_id(sender, True)
        
        # Clean up dead weakrefs if any (though we handle it during iteration)
        to_remove = []
        
        for i, (r_id, s_id, uid) in enumerate(self._live_receivers):
            # Check sender filter
            if s_id is not None and s_id != sender_id:
                continue

            receiver = self._get_receiver(r_id)
            if receiver is None:
                to_remove.append(i)
                continue

            try:
                if asyncio.iscoroutinefunction(receiver):
                    res = await receiver(sender=sender, instance=instance, **kwargs)
                else:
                    res = receiver(sender=sender, instance=instance, **kwargs)
                responses.append((receiver, res))
            except Exception as e:
                logger.error(f"Error in signal receiver {receiver}: {e}", exc_info=True)
                responses.append((receiver, e))

        for i in reversed(to_remove):
            self._live_receivers.pop(i)
            
        return responses

    def _make_id(self, target: Any, weak: bool) -> Any:
        if weak:
            if inspect.ismethod(target):
                return weakref.WeakMethod(target)
            return weakref.ref(target)
        return target

    def _get_receiver(self, r_id: Any) -> Optional[Callable]:
        if isinstance(r_id, (weakref.ReferenceType, weakref.WeakMethod)):
            return r_id()
        return r_id

# Global Signals
pre_init = Signal("pre_init")
post_init = Signal("post_init")
pre_save = Signal("pre_save")
post_save = Signal("post_save")
pre_delete = Signal("pre_delete")
post_delete = Signal("post_delete")
pre_bulk_update = Signal("pre_bulk_update")
post_bulk_update = Signal("post_bulk_update")
pre_bulk_delete = Signal("pre_bulk_delete")
post_bulk_delete = Signal("post_bulk_delete")
m2m_changed = Signal("m2m_changed")

def receiver(signal: Union[Signal, List[Signal]], sender: Optional[Type[Any]] = None, **kwargs: Any) -> Callable:
    """
    Decorator for connecting a function to a signal.
    
    Example:
        @receiver(post_save, sender=User)
        async def on_user_saved(sender, instance, **kwargs):
            print(f"User {instance.id} saved")
    """
    def decorator(func: Callable) -> Callable:
        signals = signal if isinstance(signal, list) else [signal]
        for s in signals:
            s.connect(func, sender=sender, **kwargs)
        return func
    return decorator
