"""
Eden — Tenancy Lifecycle Signals

Provides a lightweight event dispatcher for tenant lifecycle hooks, allowing
developers to run custom logic when tenants are provisioned, activated,
or deleted.
"""

from typing import Any, Callable, Coroutine, List

class Signal:
    """
    A simple asynchronous signal dispatcher.
    
    Handlers must be async functions.
    """
    def __init__(self, name: str):
        self.name = name
        self.receivers: List[Callable[..., Coroutine[Any, Any, Any]]] = []

    def connect(self, receiver: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        """
        Decorator to attach a receiver to this signal.
        """
        if receiver not in self.receivers:
            self.receivers.append(receiver)
        return receiver

    def disconnect(self, receiver: Callable[..., Coroutine[Any, Any, Any]]) -> bool:
        """
        Disconnect a receiver from a signal.
        """
        try:
            self.receivers.remove(receiver)
            return True
        except ValueError:
            return False

    async def send(self, *args: Any, **kwargs: Any) -> List[Any]:
        """
        Send a signal to all connected receivers, sequentially awaiting them.
        Exceptions raised by receivers are logged but do not interrupt the flow.
        """
        results = []
        for receiver in self.receivers:
            try:
                result = await receiver(*args, **kwargs)
                results.append(result)
            except Exception as e:
                import logging
                log = logging.getLogger(__name__)
                log.error(f"Error in signal {self.name} receiver {receiver.__name__}: {e}", exc_info=True)
                results.append(e)
        return results


# Default Tenant Lifecycle Signals

# Fired after a tenant is first inserted into the database.
tenant_created = Signal("tenant_created")

# Fired after a tenant's database schema has been fully provisioned and tables created.
tenant_schema_provisioned = Signal("tenant_schema_provisioned")

# Fired when a tenant's is_active property flips to False.
tenant_deactivated = Signal("tenant_deactivated")

# Fired before a tenant and their schema is permanently deleted.
tenant_deleted = Signal("tenant_deleted")
