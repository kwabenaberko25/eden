from eden.websocket.manager import ConnectionManager, connection_manager

# Alias for backward compatibility
manager = connection_manager
realtime_manager = connection_manager

__all__ = ["ConnectionManager", "realtime_manager", "manager"]
