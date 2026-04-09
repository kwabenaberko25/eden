"""
Eden Framework — Feature Flags Admin UI

Web dashboard for managing feature flags with real-time status,
CRUD operations, and gradual rollout controls.

**Features:**
- List all flags with current status
- Create/edit/delete flags
- Adjust rollout percentages in real-time
- View flag history and metrics
- Environment-specific controls
- API endpoints for integration

**Usage:**

    from eden.admin.flags import FlagsAdminPanel
    from fastapi import FastAPI
    
    app = FastAPI()
    admin = FlagsAdminPanel(manager=flag_manager)
    
    # Mount routes
    app.include_router(admin.router, prefix="/admin/flags")
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

from eden import Router as APIRouter, HttpException as HTTPException, Depends
from eden.requests import Request
from pydantic import BaseModel, Field

from eden.flags import FlagManager, Flag, FlagStrategy

logger = logging.getLogger(__name__)


# ============================================================================
# Schemas
# ============================================================================

class FlagStrategyStr(str, Enum):
    """String representation of flag strategies."""
    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    PERCENTAGE = "percentage"
    USER_ID = "user_id"
    USER_SEGMENT = "user_segment"
    TENANT_ID = "tenant_id"
    ENVIRONMENT = "environment"


class FlagCreate(BaseModel):
    """Create flag request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    strategy: FlagStrategyStr
    percentage: Optional[int] = Field(None, ge=0, le=100)
    user_ids: Optional[List[str]] = None
    segments: Optional[List[str]] = None
    tenant_ids: Optional[List[str]] = None
    environments: Optional[List[str]] = None
    enabled: bool = True


class FlagUpdate(BaseModel):
    """Update flag request."""
    description: Optional[str] = None
    percentage: Optional[int] = Field(None, ge=0, le=100)
    enabled: Optional[bool] = None


class FlagResponse(BaseModel):
    """Flag response."""
    id: str
    name: str
    description: Optional[str]
    strategy: str
    percentage: Optional[int]
    enabled: bool
    created_at: str
    updated_at: str
    usage_count: int


class FlagMetrics(BaseModel):
    """Flag metrics."""
    flag_id: str
    total_checks: int
    enabled_count: int
    disabled_count: int
    error_count: int


class FlagsStatsResponse(BaseModel):
    """Statistics response."""
    total_flags: int
    enabled_flags: int
    disabled_flags: int
    by_strategy: Dict[str, int]
    by_environment: Dict[str, int]


# ============================================================================
# In-Memory Flag Store Extension
# ============================================================================

@dataclass
class FlagMetadata:
    """Additional metadata for flags."""
    created_at: datetime
    updated_at: datetime
    usage_count: int = 0
    enabled_count: int = 0
    disabled_count: int = 0
    error_count: int = 0


# ============================================================================
# Admin Panel
# ============================================================================

class FlagsAdminPanel:
    """Admin UI for feature flags."""
    
    def __init__(self, manager: Optional[FlagManager] = None, enable_history: bool = True):
        """
        Initialize admin panel.
        
        Args:
            manager: FlagManager instance (defaults to global manager)
            enable_history: Enable flag change history
        """
        if manager is None:
            from eden.flags import get_flag_manager
            manager = get_flag_manager()
        
        self.manager = manager
        self.enable_history = enable_history
        self.router = APIRouter()
        self.flag_metadata: Dict[str, FlagMetadata] = {}
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes to match test expectations."""
        # Tests expect GET /admin/flags to be list and GET /admin/flags/ to be stats
        # We disambiguate names to avoid Eden route name collisions
        self.router.get("", name="list_flags_api")(self.list_flags)
        self.router.get("/", name="get_stats_api")(self.get_stats)
        
        # POST /admin/flags for creation
        self.router.post("", name="create_flag_api")(self.create_flag)
        self.router.post("/", name="create_flag_api_slash")(self.create_flag)
        
        # Other routes
        self.router.get("/{flag_id}", name="get_flag_api")(self.get_flag)
        self.router.patch("/{flag_id}", name="update_flag_api")(self.update_flag)
        self.router.delete("/{flag_id}", name="delete_flag_api")(self.delete_flag)
        self.router.get("/{flag_id}/metrics", name="get_metrics_api")(self.get_metrics)
        self.router.post("/{flag_id}/enable", name="enable_flag_api")(self.enable_flag)
        self.router.post("/{flag_id}/disable", name="disable_flag_api")(self.disable_flag)
    
    async def get_stats(self) -> FlagsStatsResponse:
        """Get overall statistics."""
        flags = await self.manager.get_all_flags()
        
        by_strategy = {}
        by_environment = {}
        
        for flag in flags.values():
            strategy = flag.strategy.value
            by_strategy[strategy] = by_strategy.get(strategy, 0) + 1
            
            if flag.environments:
                for env in flag.environments:
                    by_environment[env] = by_environment.get(env, 0) + 1
        
        return FlagsStatsResponse(
            total_flags=len(flags),
            enabled_flags=sum(1 for f in flags.values() if f.enabled),
            disabled_flags=sum(1 for f in flags.values() if not f.enabled),
            by_strategy=by_strategy,
            by_environment=by_environment,
        )
    
    async def list_flags(self, request: Request) -> List[FlagResponse]:
        """List all flags with filtering."""
        strategy = request.query_params.get("strategy")
        enabled_str = request.query_params.get("enabled")
        enabled = None
        if enabled_str is not None:
            enabled = enabled_str.lower() in ("true", "1", "yes")
        skip = int(request.query_params.get("skip", 0))
        limit = int(request.query_params.get("limit", 50))
        flags = await self.manager.get_all_flags()
        results = []
        
        for flag_id, flag in flags.items():
            # Apply filters
            if strategy and flag.strategy.value != strategy:
                continue
            if enabled is not None and flag.enabled != enabled:
                continue
            
            metadata = self.flag_metadata.get(flag_id, FlagMetadata(
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ))
            
            results.append(FlagResponse(
                id=flag_id,
                name=flag.name,
                description=flag.description,
                strategy=flag.strategy.value,
                percentage=flag.percentage,
                enabled=flag.enabled,
                created_at=metadata.created_at.isoformat(),
                updated_at=metadata.updated_at.isoformat(),
                usage_count=metadata.usage_count,
            ))
        
        # Pagination
        return results[skip : skip + limit]
    
    async def create_flag(self, request: Request) -> FlagResponse:
        """Create a new flag."""
        data = await request.json()
        req = FlagCreate(**data)
        flag_id = req.name
        
        # Check if exists
        if flag_id in await self.manager.get_all_flags():
            raise HTTPException(status_code=409, detail="Flag already exists")
        
        # Map strategy
        strategy_map = {
            FlagStrategyStr.ALWAYS_ON: FlagStrategy.ALWAYS_ON,
            FlagStrategyStr.ALWAYS_OFF: FlagStrategy.ALWAYS_OFF,
            FlagStrategyStr.PERCENTAGE: FlagStrategy.PERCENTAGE,
            FlagStrategyStr.USER_ID: FlagStrategy.USER_ID,
            FlagStrategyStr.USER_SEGMENT: FlagStrategy.USER_SEGMENT,
            FlagStrategyStr.TENANT_ID: FlagStrategy.TENANT_ID,
            FlagStrategyStr.ENVIRONMENT: FlagStrategy.ENVIRONMENT,
        }
        
        # Create flag
        flag = Flag(
            name=flag_id,
            strategy=strategy_map[req.strategy],
            description=req.description or "",
            percentage=req.percentage,
            allowed_user_ids=req.user_ids,
            allowed_segments=req.segments,
            allowed_tenants=req.tenant_ids,
            environments=req.environments,
            enabled=req.enabled,
        )
        
        self.manager.register_flag(flag)
        self.flag_metadata[flag_id] = FlagMetadata(
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        logger.info(f"Flag created: {flag_id}")
        
        return FlagResponse(
            id=flag_id,
            name=flag.name,
            description=flag.description,
            strategy=flag.strategy.value,
            percentage=flag.percentage,
            enabled=flag.enabled,
            created_at=self.flag_metadata[flag_id].created_at.isoformat(),
            updated_at=self.flag_metadata[flag_id].updated_at.isoformat(),
            usage_count=0,
        )
    
    async def get_flag(self, flag_id: str) -> FlagResponse:
        """Get a specific flag."""
        flags = await self.manager.get_all_flags()
        
        if flag_id not in flags:
            raise HTTPException(status_code=404, detail="Flag not found")
        
        flag = flags[flag_id]
        metadata = self.flag_metadata.get(flag_id, FlagMetadata(
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ))
        
        return FlagResponse(
            id=flag_id,
            name=flag.name,
            description=flag.description,
            strategy=flag.strategy.value,
            percentage=flag.percentage,
            enabled=flag.enabled,
            created_at=metadata.created_at.isoformat(),
            updated_at=metadata.updated_at.isoformat(),
            usage_count=metadata.usage_count,
        )
    
    async def update_flag(self, flag_id: str, request: Request) -> FlagResponse:
        """Update a flag."""
        data = await request.json()
        req = FlagUpdate(**data)
        flags = await self.manager.get_all_flags()
        
        if flag_id not in flags:
            raise HTTPException(status_code=404, detail="Flag not found")
        
        flag = flags[flag_id]
        
        # Update fields
        if req.description is not None:
            flag.description = req.description
        if req.percentage is not None:
            flag.percentage = req.percentage
        if req.enabled is not None:
            flag.enabled = req.enabled
        
        # Update metadata
        if flag_id not in self.flag_metadata:
            self.flag_metadata[flag_id] = FlagMetadata(
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        self.flag_metadata[flag_id].updated_at = datetime.now()
        
        logger.info(f"Flag updated: {flag_id}")
        
        return FlagResponse(
            id=flag_id,
            name=flag.name,
            description=flag.description,
            strategy=flag.strategy.value,
            percentage=flag.percentage,
            enabled=flag.enabled,
            created_at=self.flag_metadata[flag_id].created_at.isoformat(),
            updated_at=self.flag_metadata[flag_id].updated_at.isoformat(),
            usage_count=self.flag_metadata[flag_id].usage_count,
        )
    
    async def delete_flag(self, flag_id: str):
        """Delete a flag."""
        flags = await self.manager.get_all_flags()
        
        if flag_id not in flags:
            raise HTTPException(status_code=404, detail="Flag not found")
        
        # Remove from manager
        del flags[flag_id]
        
        # Remove metadata
        if flag_id in self.flag_metadata:
            del self.flag_metadata[flag_id]
        
        logger.info(f"Flag deleted: {flag_id}")
        
        return {"status": "deleted", "flag_id": flag_id}
    
    async def get_metrics(self, flag_id: str) -> FlagMetrics:
        """Get metrics for a flag."""
        if flag_id not in await self.manager.get_all_flags():
            raise HTTPException(status_code=404, detail="Flag not found")
        
        metadata = self.flag_metadata.get(flag_id, FlagMetadata(
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ))
        
        return FlagMetrics(
            flag_id=flag_id,
            total_checks=metadata.usage_count,
            enabled_count=metadata.enabled_count,
            disabled_count=metadata.disabled_count,
            error_count=metadata.error_count,
        )
    
    async def enable_flag(self, flag_id: str):
        """Enable a flag."""
        flags = await self.manager.get_all_flags()
        
        if flag_id not in flags:
            raise HTTPException(status_code=404, detail="Flag not found")
        
        flags[flag_id].enabled = True
        
        if flag_id in self.flag_metadata:
            self.flag_metadata[flag_id].updated_at = datetime.now()
        
        logger.info(f"Flag enabled: {flag_id}")
        
        return {"status": "enabled", "flag_id": flag_id}
    
    async def disable_flag(self, flag_id: str):
        """Disable a flag."""
        flags = await self.manager.get_all_flags()
        
        if flag_id not in flags:
            raise HTTPException(status_code=404, detail="Flag not found")
        
        flags[flag_id].enabled = False
        
        if flag_id in self.flag_metadata:
            self.flag_metadata[flag_id].updated_at = datetime.now()
        
        logger.info(f"Flag disabled: {flag_id}")
        
        return {"status": "disabled", "flag_id": flag_id}
