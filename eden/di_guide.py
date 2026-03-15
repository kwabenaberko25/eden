r'''
Eden Dependency Injection — Complete Guide

Eden provides FastAPI-style dependency injection with support for:
- Simple callable dependencies
- Async/sync generators with cleanup (yield-based)
- Context managers (async/sync with automatic __aexit__ calling)
- Nested sub-dependencies (dependencies of dependencies)
- Per-request caching (each dependency resolved once per request)
- Circular dependency detection
- Type coercion with complex types (Optional, Union, List, etc.)
- Proper async context manager cleanup with __aexit__
- Lazy loading (future feature)

═══════════════════════════════════════════════════════════════════════════════

THE BASICS

Example usage:

    from eden.dependencies import Depends

The Depends() marker tells Eden how to resolve a parameter:

    from eden.dependencies import Depends
    
    async def get_db():
        """Dependency that provides database access."""
        db = await connect_to_db()
        try:
            yield db
        finally:
            await db.close()
    
    @app.get("/users")
    async def list_users(db=Depends(get_db)):
        # db is automatically resolved and provided by the DI system
        users = await db.query(User).all()
        return users

═══════════════════════════════════════════════════════════════════════════════

BUILT-IN INJECTIONS (No Depends() Needed)

These are automatically resolved and injected:

1. Request Object
    @app.get("/")
    async def handler(request):
        # Automatically provided!
        return {"path": request.url.path}

2. Application State
    @app.get("/config")
    async def get_config(state):
        # app.state automatically injected
        return {"debug": state.debug_mode}

3. Application Instance
    @app.get("/ping")
    async def ping(app):
        # app instance automatically injected
        return {"version": app.version}

4. Database Session (AsyncSession)
    @app.get("/users")
    async def list_users(session):
        # AsyncSession automatically acquired from context or app.state.db
        users = await session.query(User).all()
        return users

Note:  These work because they match parameter names or annotations.
    - request: Request
    - state: Any (from app.state)
    - app: Starlette/FastAPI application
    - session: AsyncSession

═══════════════════════════════════════════════════════════════════════════════

DEPENDENCY PATTERNS

Pattern 1: Simple Callable
────────────────────────
Returns a value directly (no cleanup needed).

    def get_current_user_id(request):
        """Extract user ID from auth header."""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            # Validate and extract user ID
            return int(token) if token.isdigit() else None
        return None
    
    @app.get("/profile")
    async def get_profile(user_id: int = Depends(get_current_user_id)):
        if not user_id:
            return {"error": "Not authenticated"}
        user = await User.get(user_id)
        return user

Pattern 2: Async Callable
─────────────────────────
Async function that returns a value.

    async def get_current_user(request):
        """Fetch current user from database using auth token."""
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return None
        
        # Async operation
        user = await User.filter(auth_token=token).first()
        return user
    
    @app.get("/profile")
    async def get_profile(user=Depends(get_current_user)):
        if not user:
            return {"error": "Not authenticated"}
        return user.to_dict()

Pattern 3: Generator (Cleanup)
──────────────────────────────
Use yield for setup/cleanup. Code before yield runs on entry,
after yield runs on exit (cleanup).

    def get_redis_connection():
        """Provides and cleans up Redis connection."""
        conn = redis.Redis()
        try:
            yield conn
        finally:
            conn.close()  # Cleanup
    
    @app.post("/cache/clear")
    async def clear_cache(redis=Depends(get_redis_connection)):
        redis.delete("*")  # Use the connection
        return {"status": "cleared"}
    # Cleanup happens automatically after handler returns

Pattern 4: Async Generator (Async Cleanup)
──────────────────────────────────────────
Same as generator but supports async cleanup operations.

    async def get_db():
        """Provides and cleans up async database connection."""
        db = await AsyncDatabase.connect()
        try:
            yield db
        finally:
            await db.close()  # Async cleanup
    
    @app.get("/users")
    async def list_users(db=Depends(get_db)):
        return await db.query(User).all()

Pattern 5: Nested Dependencies
──────────────────────────────
Dependencies can depend on other dependencies.

    async def get_database():
        """Get database connection."""
        db = await connect()
        try:
            yield db
        finally:
            await db.close()
    
    async def get_current_user(db=Depends(get_database), request):
        """Fetch current user from database."""
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = await db.query(User).filter_by(auth_token=token).first()
        return user
    
    @app.get("/profile")
    async def get_profile(user=Depends(get_current_user)):
        # get_current_user depends on get_database
        # Both are automatically resolved and injected
        return user.to_dict()

Pattern 6: Cached Dependencies
──────────────────────────────
By default, dependencies are cached per-request. The same dependency
resolved multiple times within one request returns the same instance.

    def get_config():
        """Returns app configuration."""
        print("Loading config...")  # Prints once per request
        return {"debug": True, "max_items": 100}
    
    @app.get("/")
    async def handler(
        config1=Depends(get_config),  # Calls get_config, prints once
        config2=Depends(get_config),  # Returns cached instance, doesn't print
    ):
        assert config1 is config2  # True! Same object
        return config1

Pattern 7: Multiple Dependencies
────────────────────────────────
Routes can have many dependencies.

    @app.post("/posts")
    async def create_post(
        user=Depends(get_current_user),
        db=Depends(get_db),
        cache=Depends(get_redis),
    ):
        # All three dependencies automatically resolved
        post = Post(author_id=user.id, title="...")
        await db.save(post)
        await cache.invalidate("posts_list")
        return post

═══════════════════════════════════════════════════════════════════════════════

ADVANCED: DEPENDENCY RESOLVER

The DependencyResolver resolves all dependencies for a function.
It's usually called automatically by route handlers but can be used manually:

    from eden.dependencies import DependencyResolver, Depends
    
    async def get_db():
        db = await connect()
        try:
            yield db
        finally:
            await db.close()
    
    async def my_function(db=Depends(get_db)):
        return await db.query(User).all()
    
    # Manual resolution
    resolver = DependencyResolver()
    try:
        kwargs = await resolver.resolve(
            my_function,
            request=current_request,
            app=current_app
        )
        result = await my_function(**kwargs)
    finally:
        await resolver.cleanup()  # Important: cleanup generators and context managers

═══════════════════════════════════════════════════════════════════════════════

CIRCULAR DEPENDENCY DETECTION

Eden detects circular dependencies and raises CircularDependencyError:

    # ❌ BROKEN: Circular dependency
    async def get_user(role=Depends(get_role)):
        ...
    
    async def get_role(user=Depends(get_user)):
        ...
    
    @app.get("/")
    async def handler(user=Depends(get_user)):
        # Raises: CircularDependencyError: Circular dependency detected: get_user -> get_role -> get_user
        pass
    
    # ✅ FIX: Break the cycle
    async def get_user():
        # Don't depend on get_role here
        user = await User.first()
        return user
    
    async def get_user_role(user=Depends(get_user)):
        # OK: depends on get_user, get_user doesn't depend on this
        return await Role.get(user.role_id)

═══════════════════════════════════════════════════════════════════════════════

TYPE COERCION

Eden automatically coerces path/query parameters to the annotation type:

    @app.get("/users/{user_id}")
    async def get_user(
        user_id: int,  # Automatically converted from string to int
        is_admin: bool = False,  # Query param converted to bool
    ):
        user = await User.get(user_id)
        return user
    
    # Supported types:
    # - str, int, float, bool            (basic types)
    # - Optional[T], Union[T, U]         (nullable/choice types)
    # - List[T]                          (lists, coerces each item to T)
    # - Pydantic models                  (calls model_validate)

═══════════════════════════════════════════════════════════════════════════════

REAL-WORLD EXAMPLE: Complete User Authentication Flow

    from eden.dependencies import Depends
    from eden.requests import Request
    from eden.responses import JsonResponse
    
    async def get_db():
        """Provide database connection."""
        db = await AsyncDB.connect()
        try:
            yield db
        finally:
            await db.close()
    
    async def get_current_user(request: Request, db=Depends(get_db)):
        """Extract and validate current user from JWT token."""
        # 1. Get token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]
        
        # 2. Decode and validate JWT
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return None
        
        user_id = payload.get("user_id")
        
        # 3. Fetch user from database
        user = await db.query(User).filter_by(id=user_id).first()
        if not user or not user.is_active:
            return None
        
        return user
    
    async def get_admin_user(user=Depends(get_current_user)):
        """Require admin user."""
        if not user:
            raise Forbidden("Not authenticated")
        if not user.is_admin:
            raise Forbidden("Admin access required")
        return user
    
    async def get_redis():
        """Provide Redis cache."""
        redis = aioredis.from_url("redis://localhost")
        try:
            yield redis
        finally:
            await redis.close()
    
    # Route 1: Public endpoint
    @app.get("/users/{user_id}")
    async def get_user_public(user_id: int):
        user = await User.get(user_id)
        if not user:
            return JsonResponse({"error": "Not found"}, status_code=404)
        return user.to_dict()
    
    # Route 2: Requires authentication
    @app.get("/profile")
    async def get_profile(user=Depends(get_current_user)):
        if not user:
            return JsonResponse({"error": "Not authenticated"}, status_code=401)
        return user.to_dict()
    
    # Route 3: Admin only
    @app.delete("/users/{user_id}")
    async def delete_user(
        user_id: int,
        admin=Depends(get_admin_user),
        db=Depends(get_db),
    ):
        # admin is the current user (validated as admin above)
        target_user = await db.query(User).get(user_id)
        if not target_user:
            return JsonResponse({"error": "Not found"}, status_code=404)
        
        await db.delete(target_user)
        return {"deleted": user_id}
    
    # Route 4: Multiple dependencies with caching
    @app.post("/cache/invalidate")
    async def invalidate_cache(
        admin=Depends(get_admin_user),
        redis=Depends(get_redis),  # Resolved and cached per request
        cache_key: str = "orders",
    ):
        # Redis connection from get_redis is used here
        await redis.delete(cache_key)
        return {"invalidated": cache_key}
        # get_redis cleanup happens automatically after response

═══════════════════════════════════════════════════════════════════════════════

COMMON MISTAKES & SOLUTIONS

Mistake 1: Forgetting to yield in a generator
────────────────────────────────────────────
    # ❌ WRONG: Never yields
    def get_db():
        db = connect()
        # Oops! Forgot to yield
        db.close()
    
    # ✅ CORRECT: Yields and cleans up
    def get_db():
        db = connect()
        try:
            yield db
        finally:
            db.close()

Mistake 2: Not awaiting async operations
────────────────────────────────────────
    # ❌ WRONG: Not async
    def get_user(request):
        # This is synchronous but returns an async operation
        return User.get(123)  # Returns a coroutine, not a User!
    
    # ✅ CORRECT: Async function
    async def get_user(request):
        return await User.get(123)  # Actually waits for User

Mistake 3: Circular dependencies
─────────────────────────────────
    # ❌ WRONG: Circular
    async def get_user(role=Depends(get_role)):
        ...
    async def get_role(user=Depends(get_user)):
        ...
    
    # ✅ CORRECT: Linear chain
    async def get_user():
        ...
    async def get_role(user=Depends(get_user)):
        ...

Mistake 4: Not calling cleanup in manual resolution
────────────────────────────────────────────────────
    # ❌ WRONG: Cleanup never called
    resolver = DependencyResolver()
    kwargs = await resolver.resolve(my_func)
    result = await my_func(**kwargs)
    # Generators/context managers never cleaned up!
    
    # ✅ CORRECT: Always clean up
    resolver = DependencyResolver()
    try:
        kwargs = await resolver.resolve(my_func)
        result = await my_func(**kwargs)
    finally:
        await resolver.cleanup()

═══════════════════════════════════════════════════════════════════════════════

TESTING WITH DEPENDENCIES

Override dependencies for testing:

    from unittest.mock import AsyncMock
    from eden.testing import TestClient
    
    async def mock_get_user():
        return User(id=1, name="Test User", is_admin=True)
    
    client = TestClient(app)
    # Override dependency for all requests in test
    client.app.dependency_overrides = {
        get_current_user: mock_get_user
    }
    
    response = client.get("/admin/stats")
    assert response.status_code == 200
    # Now the test uses mock_get_user instead of the real get_current_user

═══════════════════════════════════════════════════════════════════════════════

BEST PRACTICES

1. Use dependencies for cross-cutting concerns (auth, logging, db access)
2. Keep dependencies simple and focused (single responsibility)
3. Use async/generators for resources that need cleanup
4. Leverage caching for expensive operations (DB queries, API calls)
5. Document what each dependency returns and requires
6. Use type hints so IDE autocomplete works
7. Test dependencies in isolation
8. Don't make dependencies do too much (complex business logic belongs in services)
'''

# This is documentation only. Implementation is in eden.dependencies module.
