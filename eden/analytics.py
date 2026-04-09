"""
Eden Framework — Analytics Provider Framework

Plugin architecture for external analytics services.

Supports:
- Multiple providers simultaneously
- Automatic request/error tracking
- Custom event tracking
- Batch processing for performance

**Usage:**

    from eden.analytics import AnalyticsManager, GoogleAnalyticsProvider
    
    # Configure
    analytics = AnalyticsManager()
    analytics.add_provider(GoogleAnalyticsProvider(tracking_id="UA-12345678-1"))
    
    # Track events
    await analytics.track_event("user_signup", {"plan": "pro"})
    await analytics.track_user("user123", {"email": "user@example.com"})
    await analytics.track_page("/dashboard", {"referrer": "/login"})
    
    # Flush all providers
    await analytics.flush()
"""

import logging
from typing import Any, Dict, Optional, List, Type
from abc import ABC, abstractmethod
from datetime import datetime
import json
import asyncio

logger = logging.getLogger(__name__)


# ============================================================================
# Base Provider
# ============================================================================

class AnalyticsProvider(ABC):
    """Abstract base for analytics providers."""
    
    name: str = "analytics"
    enabled: bool = True
    batch_size: int = 100
    
    def __init__(self):
        self.queue: List[Dict[str, Any]] = []
        self._flushing = False
    
    @abstractmethod
    async def track_event(self, event_name: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Track a custom event."""
        pass
    
    @abstractmethod
    async def track_user(self, user_id: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Track user information."""
        pass
    
    @abstractmethod
    async def track_page(self, url: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Track page view."""
        pass
    
    @abstractmethod
    async def identify(self, user_id: str, **traits) -> None:
        """Identify a user."""
        pass
    
    @abstractmethod
    async def flush(self) -> None:
        """Flush queued events to provider."""
        pass
    
    async def _queue_event(self, event: Dict[str, Any]) -> None:
        """Add event to queue."""
        self.queue.append(event)
        if len(self.queue) >= self.batch_size:
            await self.flush()


# ============================================================================
# Built-in Providers
# ============================================================================

class NoOpProvider(AnalyticsProvider):
    """No-op provider for development/testing."""
    
    name = "noop"
    
    async def track_event(self, event_name: str, properties: Optional[Dict[str, Any]] = None) -> None:
        logger.debug(f"[NoOp] Event: {event_name} {properties}")
    
    async def track_user(self, user_id: str, properties: Optional[Dict[str, Any]] = None) -> None:
        logger.debug(f"[NoOp] User: {user_id} {properties}")
    
    async def track_page(self, url: str, properties: Optional[Dict[str, Any]] = None) -> None:
        logger.debug(f"[NoOp] Page: {url} {properties}")
    
    async def identify(self, user_id: str, **traits) -> None:
        logger.debug(f"[NoOp] Identify: {user_id} {traits}")
    
    async def flush(self) -> None:
        pass


class GoogleAnalyticsProvider(AnalyticsProvider):
    """Google Analytics provider (stub)."""
    
    name = "google_analytics"
    
    def __init__(self, tracking_id: str, api_version: str = "v1"):
        """
        Initialize Google Analytics provider.
        
        Args:
            tracking_id: Google Analytics tracking ID (e.g., "UA-12345678-1" or "G-XXXXXXXXXX")
            api_version: Analytics API version
        """
        super().__init__()
        self.tracking_id = tracking_id
        self.api_version = api_version
        self.endpoint = "https://www.google-analytics.com/collect"
    
    async def track_event(self, event_name: str, properties: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "type": "event",
            "name": event_name,
            "properties": properties or {},
            "timestamp": datetime.now().isoformat(),
        }
        await self._queue_event(event)
    
    async def track_user(self, user_id: str, properties: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "type": "user",
            "user_id": user_id,
            "properties": properties or {},
            "timestamp": datetime.now().isoformat(),
        }
        await self._queue_event(event)
    
    async def track_page(self, url: str, properties: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "type": "page",
            "url": url,
            "properties": properties or {},
            "timestamp": datetime.now().isoformat(),
        }
        await self._queue_event(event)
    
    async def identify(self, user_id: str, **traits) -> None:
        event = {
            "type": "identify",
            "user_id": user_id,
            "traits": traits,
            "timestamp": datetime.now().isoformat(),
        }
        await self._queue_event(event)
    
    async def flush(self) -> None:
        """Flush to Google Analytics (stub implementation)."""
        if not self.queue:
            return
        
        logger.debug(f"Flushing {len(self.queue)} events to Google Analytics")
        # In real implementation, would batch send to GA endpoint
        self.queue.clear()


class SegmentProvider(AnalyticsProvider):
    """Segment analytics provider (stub)."""
    
    name = "segment"
    
    def __init__(self, write_key: str):
        """
        Initialize Segment provider.
        
        Args:
            write_key: Segment write key
        """
        super().__init__()
        self.write_key = write_key
        self.endpoint = "https://api.segment.io/v1"
    
    async def track_event(self, event_name: str, properties: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "type": "track",
            "event": event_name,
            "properties": properties or {},
            "timestamp": datetime.now().isoformat(),
        }
        await self._queue_event(event)
    
    async def track_user(self, user_id: str, properties: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "type": "identify",
            "userId": user_id,
            "traits": properties or {},
            "timestamp": datetime.now().isoformat(),
        }
        await self._queue_event(event)
    
    async def track_page(self, url: str, properties: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "type": "page",
            "properties": {**(properties or {}), "url": url},
            "timestamp": datetime.now().isoformat(),
        }
        await self._queue_event(event)
    
    async def identify(self, user_id: str, **traits) -> None:
        event = {
            "type": "identify",
            "userId": user_id,
            "traits": traits,
            "timestamp": datetime.now().isoformat(),
        }
        await self._queue_event(event)
    
    async def flush(self) -> None:
        """Flush to Segment (stub implementation)."""
        if not self.queue:
            return
        
        logger.debug(f"Flushing {len(self.queue)} events to Segment")
        # In real implementation, would batch send to Segment API
        self.queue.clear()


class MixpanelProvider(AnalyticsProvider):
    """Mixpanel analytics provider (stub)."""
    
    name = "mixpanel"
    
    def __init__(self, token: str):
        """
        Initialize Mixpanel provider.
        
        Args:
            token: Mixpanel project token
        """
        super().__init__()
        self.token = token
        self.endpoint = "https://api.mixpanel.com"
    
    async def track_event(self, event_name: str, properties: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "type": "track",
            "event": event_name,
            "properties": {**(properties or {}), "token": self.token},
        }
        await self._queue_event(event)
    
    async def track_user(self, user_id: str, properties: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "type": "user",
            "user_id": user_id,
            "properties": properties or {},
        }
        await self._queue_event(event)
    
    async def track_page(self, url: str, properties: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "type": "page",
            "url": url,
            "properties": properties or {},
        }
        await self._queue_event(event)
    
    async def identify(self, user_id: str, **traits) -> None:
        event = {
            "type": "identify",
            "user_id": user_id,
            "traits": traits,
        }
        await self._queue_event(event)
    
    async def flush(self) -> None:
        """Flush to Mixpanel (stub implementation)."""
        if not self.queue:
            return
        
        logger.debug(f"Flushing {len(self.queue)} events to Mixpanel")
        # In real implementation, would batch send to Mixpanel API
        self.queue.clear()


# ============================================================================
# Analytics Manager
# ============================================================================

class AnalyticsManager:
    """Central manager for analytics providers."""
    
    def __init__(self):
        """Initialize analytics manager."""
        self.providers: Dict[str, AnalyticsProvider] = {}
        self._flush_task = None
    
    def add_provider(self, provider: AnalyticsProvider) -> None:
        """
        Add an analytics provider.
        
        Args:
            provider: AnalyticsProvider instance
        """
        if not provider.enabled:
            logger.info(f"Provider {provider.name} is disabled, skipping")
            return
        
        self.providers[provider.name] = provider
        logger.info(f"Analytics provider added: {provider.name}")
    
    def remove_provider(self, name: str) -> None:
        """Remove a provider."""
        if name in self.providers:
            del self.providers[name]
            logger.info(f"Analytics provider removed: {name}")
    
    async def track_event(self, event_name: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Track a custom event across all providers."""
        tasks = [
            provider.track_event(event_name, properties)
            for provider in self.providers.values()
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def track_user(self, user_id: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Track user information across all providers."""
        tasks = [
            provider.track_user(user_id, properties)
            for provider in self.providers.values()
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def track_page(self, url: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Track page view across all providers."""
        tasks = [
            provider.track_page(url, properties)
            for provider in self.providers.values()
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def identify(self, user_id: str, **traits) -> None:
        """Identify user across all providers."""
        tasks = [
            provider.identify(user_id, **traits)
            for provider in self.providers.values()
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def flush(self) -> None:
        """Flush all providers."""
        tasks = [provider.flush() for provider in self.providers.values()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug("Analytics flushed")
    
    async def start_auto_flush(self, interval: int = 60) -> None:
        """
        Start automatic flushing.
        
        Args:
            interval: Flush interval in seconds
        """
        async def auto_flush():
            while True:
                await asyncio.sleep(interval)
                await self.flush()
        
        self._flush_task = asyncio.create_task(auto_flush())
        logger.info(f"Analytics auto-flush started (interval={interval}s)")
    
    async def stop_auto_flush(self) -> None:
        """Stop automatic flushing."""
        if self._flush_task:
            self._flush_task.cancel()
            logger.info("Analytics auto-flush stopped")


# ============================================================================
# Global Instance
# ============================================================================

_global_analytics: Optional[AnalyticsManager] = None


def get_analytics_manager() -> AnalyticsManager:
    """Get global analytics manager."""
    global _global_analytics
    if _global_analytics is None:
        _global_analytics = AnalyticsManager()
    return _global_analytics


def set_analytics_manager(manager: AnalyticsManager) -> None:
    """Set global analytics manager."""
    global _global_analytics
    _global_analytics = manager
