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
    
    Storage format for _live_receivers:
        Each entry is a tuple of:
        (receiver_id: int, receiver_ref: Any, sender_ref: Any, dispatch_uid: str|None)
        
        - receiver_id: The id() of the original receiver for stable identity comparison
        - receiver_ref: Either the raw callable (strong) or a weakref to it
        - sender_ref: Either None (match all senders) or a weakref to the sender class
        - dispatch_uid: Optional unique identifier for deduplication
    """

    def __init__(self, name: str):
        self.name = name
        # Each entry: (receiver_id, receiver_ref, sender_ref, dispatch_uid)
        self._live_receivers: List[tuple] = []
        # Strong reference set to prevent GC of receivers that can't be weakref'd
        # or that are explicitly connected with weak=False
        self._strong_refs: set = set()

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
        r_id = id(receiver)
        r_ref = self._make_ref(receiver, weak)
        s_ref = self._make_sender_ref(sender)
        
        entry = (r_id, r_ref, s_ref, dispatch_uid)
        
        if dispatch_uid:
            # Replace existing receiver with same dispatch_uid
            for i, (_, _, _, uid) in enumerate(self._live_receivers):
                if uid == dispatch_uid:
                    self._live_receivers[i] = entry
                    return

        self._live_receivers.append(entry)

    def disconnect(
        self,
        receiver: Optional[Callable] = None,
        sender: Optional[Type[Any]] = None,
        dispatch_uid: Optional[str] = None,
    ) -> bool:
        """
        Disconnect a receiver from this signal.
        
        Matches by dispatch_uid first (if provided), then by receiver identity
        (using id() for stable comparison even with weakrefs).
        """
        disconnected = False
        to_remove = []
        target_id = id(receiver) if receiver else None

        for i, (r_id, r_ref, s_ref, uid) in enumerate(self._live_receivers):
            if dispatch_uid and uid == dispatch_uid:
                to_remove.append(i)
                disconnected = True
                continue
            
            if target_id is not None and r_id == target_id:
                if sender is None or self._sender_matches(s_ref, sender):
                    to_remove.append(i)
                    disconnected = True
        
        for i in reversed(to_remove):
            _, r_ref, _, _ = self._live_receivers.pop(i)
            # Clean up strong reference if we held one
            self._strong_refs.discard(r_ref)
            
        return disconnected

    async def send(self, sender: Optional[Type[Any]], instance: Any, **kwargs: Any) -> List[tuple[Callable, Any]]:
        """
        Notify all connected receivers.
        Returns a list of (receiver, response) tuples.
        """
        responses = []
        to_remove = []
        
        for i, (r_id, r_ref, s_ref, uid) in enumerate(self._live_receivers):
            # Check sender filter
            if s_ref is not None:
                actual_sender = self._resolve_ref(s_ref)
                if actual_sender is None:
                    # Sender was GC'd, remove this entry
                    to_remove.append(i)
                    continue
                if actual_sender is not sender:
                    continue

            receiver = self._resolve_ref(r_ref)
            if receiver is None:
                to_remove.append(i)
                continue

            from eden.context import context_manager
            snapshot = context_manager.get_context_snapshot()

            try:
                with context_manager.baked_context(snapshot):
                    u_id = snapshot.get("user_id", "anonymous")
                    logger.debug("Dispatching signal '%s' to receiver %s (identity: %s)", 
                                 self.name, receiver.__name__, u_id)
                    
                    if inspect.iscoroutinefunction(receiver):
                        res = await receiver(sender=sender, instance=instance, **kwargs)
                    else:
                        res = receiver(sender=sender, instance=instance, **kwargs)
                    responses.append((receiver, res))
            except Exception as e:
                logger.error(f"Error in signal receiver {receiver}: {e}", exc_info=True)
                responses.append((receiver, e))

        for i in reversed(to_remove):
            _, r_ref, _, _ = self._live_receivers.pop(i)
            self._strong_refs.discard(r_ref)
            
        return responses

    def _make_ref(self, target: Any, weak: bool) -> Any:
        """
        Create a reference to a receiver.
        
        For bound methods (weak=True), uses WeakMethod to allow GC of the
        owning instance. For all other receivers (functions, lambdas, closures),
        stores a strong reference to prevent unexpected GC.
        
        Rationale: Standalone functions and lambdas have no natural "owner"
        that holds a reference to them. If we weakref them, they get GC'd
        immediately upon connect() return since the signal is often the only 
        holder. This matches Django's practical behavior.
        """
        if not weak:
            self._strong_refs.add(target)
            return target
            
        if target is None:
            return target
            
        # Only use weakref for bound methods — they have a natural owner (self)
        if inspect.ismethod(target):
            return weakref.WeakMethod(target)
        
        # For everything else (functions, lambdas, closures), use strong ref
        # to prevent immediate GC
        self._strong_refs.add(target)
        return target

    def _make_sender_ref(self, sender: Optional[Type[Any]]) -> Any:
        """Create a weak reference to a sender class, if provided."""
        if sender is None:
            return None
        try:
            return weakref.ref(sender)
        except TypeError:
            return sender

    def _resolve_ref(self, ref: Any) -> Any:
        """Dereference a weakref or return the strong reference directly."""
        if isinstance(ref, (weakref.ReferenceType, weakref.WeakMethod)):
            return ref()
        return ref

    def _sender_matches(self, s_ref: Any, sender: Type[Any]) -> bool:
        """Check if a stored sender reference matches the given sender."""
        if s_ref is None:
            return True
        actual = self._resolve_ref(s_ref)
        return actual is sender

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
