"""
Eden — Admin Panel Views

Auto-generated CRUD views for registered models.
"""

import uuid
from typing import Any

from eden.exceptions import Forbidden, NotFound
from eden.requests import Request
from eden.responses import HtmlResponse, RedirectResponse, JsonResponse, Response
from eden.admin.models import AuditLog, SupportTicket, AdminConfig
from eden.tenancy.models import Tenant
from eden.payments.models import Subscription, PaymentEvent
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


async def _get_secret_key(request: Request) -> str:
    """Consistently retrieve the secret key for JWT signing/verification."""
    # 1. Try from request.app (Eden/Starlette application)
    secret = getattr(request.app, "secret_key", None)
    if not secret and hasattr(request.app, "config"):
        secret = getattr(request.app.config, "secret_key", None)
    if secret:
        return str(secret)
    
    # 2. Try from request.app.state
    state_secret = getattr(getattr(request.app, "state", None), "secret_key", None)
    if state_secret:
        return str(state_secret)
    
    # 3. Try from global config
    try:
        from eden.config import get_config
        config = get_config()
        # Check both jwt_secret and secret_key
        secret = getattr(config, "jwt_secret", None) or getattr(config, "secret_key", None)
        if secret:
            return str(secret)
    except Exception:
        pass
        
    # 4. Fallback to insecure default (logged as error for diagnosis)
    logger.error("ADMIN: No secret key found in app or config. Falling back to insecure default.")
    return "insecure-default-secret-key-change-me"


async def _get_authenticated_user(request: Request) -> Any:
    """
    Consolidated helper to get the current user via session or JWT.
    Sets request.state.user if not already set.
    """
    # 1. Check if user is already in request.state (from session middleware)
    user = getattr(request.state, "user", None) or getattr(request, "user", None)
    if user:
        return user
        
    # 1b. Fallback for manual session check if AuthenticationMiddleware was not run
    if hasattr(request, "session") and "_auth_user_id" in request.session:
        try:
            from eden.auth.models import User
            session_db = getattr(request.app.state, "db", None)
            user = await User.get(session=session_db, id=str(request.session["_auth_user_id"]))
            if user:
                request.state.user = user
                return user
        except Exception as e:
            logger.error(f"ADMIN: Failed to load user from session: {e}")
        
    # 2. Try JWT authentication via official Backend
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        try:
            secret = await _get_secret_key(request)
            from eden.auth.backends.jwt import JWTBackend
            
            # Use Backend.authenticate which handles both decoding and DB lookup
            backend = JWTBackend(secret_key=secret)
            user = await backend.authenticate(request)
            
            if user:
                request.state.user = user
                return user
            else:
                # Log why it failed (token valid but user missing, or token invalid)
                # We can't easily distinguish without re-decoding, but we'll log the attempt
                logger.error(f"ADMIN: JWT authentication failed for header: {auth_header[:20]}...")
        except Exception as e:
            logger.exception(f"ADMIN: Unexpected error during JWT authentication: {e}")
            
    return None




async def _check_staff(request: Request) -> None:
    """Ensure the user is authenticated and is staff/superuser."""
    user = await _get_authenticated_user(request)
    
    if not user:
        from eden.exceptions import Unauthorized
        raise Unauthorized(detail="Authentication required.")
        

    if not getattr(user, "is_staff", False) and not getattr(user, "is_superuser", False):
        from eden.exceptions import Forbidden
        raise Forbidden(detail="Staff access required.")



async def _get_model_count(model_name: str) -> int:
    """Helper to get count of a model by its class name."""
    from eden.admin.models import AuditLog, SupportTicket
    from eden.tenancy.models import Tenant
    from eden.payments.models import Subscription, PaymentEvent

    model_registry = {
        "Tenant": Tenant,
        "Subscription": Subscription,
        "SupportTicket": SupportTicket,
        "AuditLog": AuditLog,
        "PaymentEvent": PaymentEvent,
    }

    model_cls = model_registry.get(model_name)
    if not model_cls:
        return 0

    try:
        if hasattr(model_cls, "include_tenantless"):
            return await model_cls.include_tenantless().count()
        return await model_cls.count()
    except Exception:
        return 0


async def admin_dashboard(request: Request, admin_site: Any) -> Response:
    """
    Render the admin dashboard with registered model counts.
    
    Args:
        request: The HTTP request.
        admin_site: The AdminSite instance with registered models.
    
    Returns:
        Response: Rendered dashboard HTML via EdenTemplates.
    """
    await _check_staff(request)

    models_info = []
    session = getattr(request.state, "db", None)

    for model, model_admin in admin_site._registry.items():
        # Use model.count() which supports auto-session injection
        try:
            count = await model.count()
        except Exception:
            # Fallback to zero if table doesn't exist or other error
            count = 0

        models_info.append({
            "name": model_admin.get_verbose_name(model),
            "name_plural": model_admin.get_verbose_name_plural(model),
            "table": model.__tablename__,
            "count": count,
            "url": f"/admin/{model.__tablename__}/",
        })

    # Fetch stats (Mock for now until BillingService is implemented)
    stats = {
        "tenants": await _get_model_count("Tenant"),
        "subscriptions": await _get_model_count("Subscription"),
        "revenue": 12540.50, # Placeholder
        "tickets": await _get_model_count("SupportTicket"),
    }

    # Fetch recent activities from AuditLog
    from eden.admin.models import AuditLog, SupportTicket
    recent_logs = await AuditLog.query().order_by("-timestamp").limit(5).all()
    activities = []
    for log in recent_logs:
        activities.append([
            log.timestamp.strftime("%m-%d %H:%M"),
            str(log.user_id)[:8] + "...",
            log.action,
            log.model_name
        ])

    return admin_site.templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "models_info": models_info,
            "stats": stats,
            "activities": activities,
            "theme": admin_site.theme,
            "title": "Admin Dashboard",
        }
    )


async def admin_list_view(
    request: Request, model: type, model_admin: Any, admin_site: Any
) -> Response:
    """Paginated list view for a model."""
    await _check_staff(request)

    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 20))
    search = request.query_params.get("q", "")

    session = getattr(request.state, "db", None)
    from eden.db import _MISSING
    qs = model.query(session or _MISSING)

    # Fetch dynamic config
    from eden.admin.models import AdminConfig
    config_obj = await AdminConfig.query().filter(model_name=model.__name__).first()
    db_config = config_obj.config if config_obj else {}

    search_fields = db_config.get("search_fields", model_admin.search_fields)
    list_display = db_config.get("list_display", model_admin.get_list_display(model))

    # Search logic
    if search and search_fields:
        from eden.db import Q
        conditions = []
        for field_name in search_fields:
            conditions.append(Q(**{f"{field_name}__icontains": search}))
        if conditions:
            combined_q = conditions[0]
            for q in conditions[1:]:
                combined_q |= q
            qs = qs.filter(combined_q)

    # Ordering
    qs = qs.order_by(*model_admin.ordering)

    # Pagination
    page_obj = await qs.paginate(page, per_page)
    
    records = page_obj.items
    total = page_obj.total
    total_pages = page_obj.total_pages

    columns = list_display
    model_name_plural = model_admin.get_verbose_name_plural(model)
    
    context = {
        "request": request,
        "model_name_plural": model_name_plural,
        "model_name": model_admin.get_verbose_name(model),
        "table_name": str(getattr(model, "__tablename__", model.__name__.lower())),
        "columns": columns,
        "records": records,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "search": search,
        "slug": model_admin.get_slug(model),
        "model_admin": model_admin,
        "has_custom_config": bool(db_config),
    }

    return admin_site.templates.TemplateResponse(request, "list.html", context)


async def admin_detail_view(
    request: Request, model: type, model_admin: Any, record_id: str, admin_site: Any
) -> Response:
    """Detail view for a single record with rich field rendering."""
    await _check_staff(request)

    session = getattr(request.state, "db", None)
    from eden.db import _MISSING
    record = await model.get(session or _MISSING, record_id)
    if not record:
        from eden.exceptions import NotFound
        raise NotFound(detail=f"Record {record_id} not found.")

    from sqlalchemy import inspect as sa_inspect
    mapper = sa_inspect(model)
    
    fields_data = []
    for col in mapper.columns:
        value = getattr(record, col.key, "")
        # Get field info from Model
        field_info = {}
        if hasattr(model, col.key):
            attr = getattr(model, col.key)
            if hasattr(attr, "info"):
                field_info = attr.info
        
        fields_data.append({
            "key": col.key,
            "label": field_info.get("label", col.key.replace("_", " ").title()),
            "value": value,
            "widget": field_info.get("widget"),
            "type": str(col.type)
        })

    model_name = model_admin.get_verbose_name(model)
    
    context = {
        "request": request,
        "model_name": model_name,
        "table_name": str(getattr(model, "__tablename__", model.__name__.lower())),
        "record_id": str(record.id),
        "fields": fields_data,
        "record": record,
        "slug": model_admin.get_slug(model),
        "model_admin": model_admin,
    }
    
    return admin_site.templates.TemplateResponse(request, "detail.html", context)

async def admin_add_view(
    request: Request, model: type, model_admin: Any, admin_site: Any
) -> Response:
    """View to create a new record."""
    await _check_staff(request)
    
    if request.method == "POST":
        form_data = await request.form()
        try:
            instance = model()
            from sqlalchemy import inspect as sa_inspect
            mapper = sa_inspect(model)
            for col in mapper.columns:
                if col.key in form_data and col.key not in model_admin.exclude_fields:
                    val = form_data[col.key]
                    if str(col.type) == "BOOLEAN":
                        val = val.lower() == "on"
                    setattr(instance, col.key, val)
            
            await model_admin.save_model(request, instance, form_data, change=False)
            
            # Save inlines with enhanced handler
            if hasattr(model_admin, "inlines"):
                from eden.admin.inline import process_inline_forms
                inline_result = await process_inline_forms(
                    dict(form_data),
                    instance,
                    model,
                    model_admin
                )
                if not inline_result["success"]:
                    logger.warning(f"Inline processing warnings: {inline_result['errors']}")

            # Log action
            user = getattr(request.state, "user", None)
            try:
                from eden.admin.models import AuditLog
                await AuditLog.log(
                    user_id=str(user.id) if user else None,
                    action="create",
                    model=model,
                    record_id=str(getattr(instance, "id", "new"))
                )
            except (ImportError, Exception):
                pass
            
            from eden.responses import RedirectResponse
            return RedirectResponse(url=f"/admin/{getattr(model, '__tablename__', model.__name__.lower())}/", status_code=303)
        except Exception as e:
            # Fallback to form with errors
            fields = await _get_fields_data(model, model_admin)
            context = {
                "request": request,
                "model_name": model_admin.get_verbose_name(model),
                "table_name": str(getattr(model, "__tablename__", model.__name__.lower())),
                "fields": fields,
                "error": str(e),
                "slug": model_admin.get_slug(model),
                "is_add": True,
            }
            return admin_site.templates.TemplateResponse(request, "form.html", context)

    fields = await _get_fields_data(model, model_admin)
    inlines = await _get_inlines_data(model, model_admin)
    context = {
        "request": request,
        "model_name": model_admin.get_verbose_name(model),
        "model_name_plural": model_admin.get_verbose_name_plural(model),
        "table_name": str(getattr(model, "__tablename__", model.__name__.lower())),
        "fields": fields,
        "inlines": inlines,
        "slug": model_admin.get_slug(model),
        "is_add": True,
    }
    return admin_site.templates.TemplateResponse(request, "form.html", context)


async def admin_edit_view(
    request: Request, model: type, model_admin: Any, record_id: str, admin_site: Any
) -> Response:
    """View to edit an existing record."""
    await _check_staff(request)

    session = getattr(request.state, "db", None)
    from eden.db import _MISSING
    record = await model.get(session or _MISSING, record_id)
    if not record:
        from eden.exceptions import NotFound
        raise NotFound(detail=f"Record {record_id} not found.")

    if request.method == "POST":
        form_data = await request.form()
        try:
            from sqlalchemy import inspect as sa_inspect
            mapper = sa_inspect(model)
            for col in mapper.columns:
                if col.key in form_data and col.key not in model_admin.exclude_fields:
                    val = form_data[col.key]
                    if str(col.type) == "BOOLEAN":
                        val = val.lower() == "on"
                    setattr(record, col.key, val)
            
            await model_admin.save_model(request, record, form_data, change=True)
            
            # Save inlines with enhanced handler
            if hasattr(model_admin, "inlines"):
                from eden.admin.inline import process_inline_forms
                inline_result = await process_inline_forms(
                    dict(form_data),
                    record,
                    model,
                    model_admin
                )
                if not inline_result["success"]:
                    logger.warning(f"Inline processing warnings: {inline_result['errors']}")

            # Log action
            user = getattr(request.state, "user", None)
            try:
                from eden.admin.models import AuditLog
                await AuditLog.log(
                    user_id=str(user.id) if user else None,
                    action="update",
                    model=model,
                    record_id=str(record_id)
                )
            except (ImportError, Exception):
                pass
            
            from eden.responses import RedirectResponse
            return RedirectResponse(url=f"/admin/{getattr(model, '__tablename__', model.__name__.lower())}/", status_code=303)
        except Exception as e:
            fields = await _get_fields_data(model, model_admin, record)
            context = {
                "request": request,
                "model_name": model_admin.get_verbose_name(model),
                "model_name_plural": model_admin.get_verbose_name_plural(model),
                "table_name": str(getattr(model, "__tablename__", model.__name__.lower())),
                "fields": fields,
                "record": record,
                "error": str(e),
                "slug": model_admin.get_slug(model),
                "is_add": False,
            }
            return admin_site.templates.TemplateResponse(request, "form.html", context)

    fields = await _get_fields_data(model, model_admin, record)
    inlines = await _get_inlines_data(model, model_admin, record)
    context = {
        "request": request,
        "model_name": model_admin.get_verbose_name(model),
        "model_name_plural": model_admin.get_verbose_name_plural(model),
        "table_name": str(getattr(model, "__tablename__", model.__name__.lower())),
        "fields": fields,
        "inlines": inlines,
        "record": record,
        "slug": model_admin.get_slug(model),
        "is_add": False,
    }
    return admin_site.templates.TemplateResponse(request, "form.html", context)


async def admin_delete_view(
    request: Request, model: type, model_admin: Any, record_id: str, admin_site: Any
) -> Response:
    """View to delete a record."""
    await _check_staff(request)

    session = getattr(request.state, "db", None)
    from eden.db import _MISSING
    record = await model.get(session or _MISSING, record_id)
    if not record:
        from eden.exceptions import NotFound
        raise NotFound(detail=f"Record {record_id} not found.")

    if request.method == "POST":
        await model_admin.delete_model(request, record)
        
        # Log action
        user = getattr(request.state, "user", None)
        try:
            from eden.admin.models import AuditLog
            await AuditLog.log(
                user_id=str(user.id) if user else None,
                action="delete",
                model=model,
                record_id=str(record_id)
            )
        except (ImportError, Exception):
            pass
            
        from eden.responses import RedirectResponse
        return RedirectResponse(url=f"/admin/{getattr(model, '__tablename__', model.__name__.lower())}/", status_code=303)

    context = {
        "request": request,
        "model_name": model_admin.get_verbose_name(model),
        "table_name": str(getattr(model, "__tablename__", model.__name__.lower())),
        "record": record,
        "record_id": record_id,
        "slug": model_admin.get_slug(model),
    }
    return admin_site.templates.TemplateResponse(request, "delete_confirm.html", context)


async def admin_action_view(
    request: Request, model: type, model_admin: Any, admin_site: Any
) -> Response:
    """Execute bulk actions via HTMX/JSON."""
    await _check_staff(request)
    from eden.responses import JsonResponse
    
    data = await request.json()
    action = data.get("action")
    ids = data.get("ids", [])
    
    if action == "delete_selected":
        session = getattr(request.state, "db", None)
        from eden.db import _MISSING
        count = await model.query(session or _MISSING).filter(id__in=ids).delete()
        return JsonResponse({"status": "ok", "message": f"Deleted {count} records"})
    
    return JsonResponse({"status": "error", "message": "Unknown action"}, status_code=400)


async def admin_login(request: Request, admin_site: Any) -> Response:
    """Login view for the admin panel."""
    error = None
    next_url = request.query_params.get("next", "/admin/")
    
    # Check if there are any superusers at all
    no_superusers = False
    try:
        from eden.auth.models import User
        from eden.db import _MISSING
        session = getattr(request.state, "db", None)
        superuser_count = await User.query(session or _MISSING).filter(
            (User.is_superuser == True) | (User.is_staff == True)
        ).count()
        if superuser_count == 0:
            no_superusers = True
    except Exception:
        pass
    
    if request.method == "POST":
        form_data = await request.form()
        email = str(form_data.get("email", "")).strip()
        password = str(form_data.get("password", "")).strip()
        
        if not email or not password:
            error = "Email and password are required."
        else:
            try:
                from eden.auth.actions import authenticate
                user = await authenticate(email=email, password=password)
                
                if user and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
                    from eden.auth.backends.session import SessionBackend
                    backend = SessionBackend()
                    await backend.login(request, user)
                    # Generate a JWT for the SPA dashboard to pick up
                    secret = await _get_secret_key(request)
                    
                    if secret:
                        from eden.auth.backends.jwt import JWTBackend
                        from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse
                        
                        jwt_backend = JWTBackend(secret_key=secret)
                        # Ensure we include test user flags if present so JWTBackend can mock
                        payload = {"sub": str(user.id)}
                        if getattr(user, "is_staff", False):
                            payload["is_staff"] = True
                        if getattr(user, "is_superuser", False):
                            payload["is_superuser"] = True
                            
                        token = jwt_backend.create_access_token(payload)
                        
                        from eden.security.urls import is_safe_url
                        if not is_safe_url(next_url, request):
                            next_url = "/admin/"

                        if "?" in next_url:
                            next_url += f"&token={token}"
                        else:
                            next_url += f"?token={token}"

                        from eden.responses import RedirectResponse
                        response = RedirectResponse(url=next_url, status_code=303)
                        
                        # Set access_token cookie
                        # Use Secure=True if the request is HTTPS
                        response.set_cookie(
                            "access_token",
                            token,
                            httponly=True,
                            secure=request.url.scheme == "https",
                            samesite="lax",
                            max_age=3600 * 24  # 24 hours
                        )
                        return response
                elif user:
                    # User exists but is not staff
                    error = "Your account does not have administrator privileges."
                else:
                    # User doesn't exist or password is wrong
                    error = "Invalid email or password."
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.exception(f"Login error for {email}: {e}")
                error = f"Authentication error: {str(e)}"
    elif no_superusers:
        error = "No administrator account exists. Please create one with: eden auth createsuperuser"
            
    context = {
        "request": request,
        "error": error,
        "next_url": next_url,
        "theme": admin_site.theme,
    }
    return admin_site.templates.TemplateResponse(request, "login.html", context)



async def admin_api_me(request: Request) -> JsonResponse:
    """
    Returns current user info for the SPA.
    Supports both session-based and JWT authentication.
    """
    # Use consolidated auth helper
    user = await _get_authenticated_user(request)
    
    if not user:
        from eden.exceptions import Unauthorized
        raise Unauthorized(detail="Not authenticated")
    
    # Map staff/superuser to roles the SPA expects
    role = "viewer"
    if getattr(user, "is_superuser", False):
        role = "admin"
    elif getattr(user, "is_staff", False):
        role = "editor"
        
    username = getattr(user, "email", None) or getattr(user, "username", None) or str(getattr(user, "id", "unknown"))
    
    return JsonResponse({
        "username": username,
        "role": role,
        "id": str(getattr(user, "id", "")),
        "is_superuser": getattr(user, "is_superuser", False)
    })


async def admin_api_logout(request: Request) -> JsonResponse:
    """
    Logout the current user and clear the JWT cookie.
    """
    from eden.auth.actions import logout
    try:
        await logout(request)
    except Exception:
        pass
        
    response = JsonResponse({"status": "ok", "message": "Logged out successfully"})
    response.delete_cookie(
        "access_token",
        path="/",
        httponly=True,
        samesite="lax"
    )
    return response

# ── Dashboard API ────────────────────────────────────────────────────

async def admin_api_dashboard(request: Request, admin_site: Any) -> JsonResponse:
    """
    Returns data for the admin dashboard, including stats, recent activities,
    and model summaries. Optimized for the PremiumAdmin SPA.
    """
    await _check_staff(request)
    session = getattr(request.state, "db", None)

    async def _count_model(name: str) -> str:
        for m in admin_site._registry:
            if m.__name__ == name:
                try:
                    qs = m.query(session)
                    if hasattr(qs, "include_tenantless"):
                        qs = qs.include_tenantless()
                    return str(await qs.count())
                except: break
        return "0"

    # 1. Fetch Stats
    stats = [
        {
            "label": "Total Tenants",
            "value": await _count_model("Tenant"),
            "icon": "fa-solid fa-building",
            "color": "var(--primary)",
            "trend": "+12%"
        },
        {
            "label": "Active Users",
            "value": await _count_model("User"),
            "icon": "fa-solid fa-users",
            "color": "#10b981",
            "trend": "+5%"
        },
        {
            "label": "Audit Entries",
            "value": await _count_model("AuditLog"),
            "icon": "fa-solid fa-clipboard-list",
            "color": "#f59e0b",
            "trend": "+8%"
        },
        {
            "label": "Feature Flags",
            "value": "8", # Hardcoded for now if not in registry
            "icon": "fa-solid fa-flag",
            "color": "#6366f1",
            "trend": "Stable"
        }
    ]
    
    # 2. Fetch Recent Activities (AuditLog)
    activities = []
    try:
        from eden.admin.models import AuditLog
        from eden.tenancy.context import AcrossTenants
        
        async with AcrossTenants():
            recent_logs = await AuditLog.query(session=session).order_by("-timestamp").limit(8).all()
            for log in recent_logs:
                activities.append({
                    "id": str(log.id),
                    "timestamp": log.timestamp.isoformat() if log.timestamp else "",
                    "time_human": log.timestamp.strftime("%m-%d %H:%M") if log.timestamp else "-",
                    "user": str(log.user_id)[:8] + "..." if log.user_id else "System",
                    "action": log.action,
                    "model": log.model_name,
                    "target_id": str(log.record_id)[:8] + "..." if log.record_id else "-"
                })
    except Exception as e:
        import logging
        logging.getLogger("eden.admin").warning(f"Failed to fetch audit logs for dashboard: {e}")
        pass

    # 3. Model Summaries (Quick counts for the grid)
    models_summary = []
    for model, model_admin in admin_site._registry.items():
        table_name = str(getattr(model, "__tablename__", model.__name__.lower()))
        try:
            # Bypass tenancy for admin dashboard counts
            qs = model.query(session)
            if hasattr(qs, "include_tenantless"):
                qs = qs.include_tenantless()
            count = await qs.count()
        except Exception:
            count = 0
            
        models_summary.append({
            "name": model.__name__,
            "table": table_name,
            "label": model_admin.get_verbose_name_plural(model),
            "label_plural": model_admin.get_verbose_name_plural(model),
            "count": count,
            "icon": getattr(model_admin, "icon", "fa-solid fa-cube"),
            "color": "var(--primary)"
        })

    return JsonResponse({
        "stats": stats,
        "models": models_summary,
        "activities": activities,
        "server_time": datetime.now().isoformat()
    })


async def admin_api_metadata(request: Request, admin_site: Any) -> JsonResponse:
    """
    Returns metadata for all registered models, including field definitions,
    available bulk actions, and nested inlines. Also includes feature flags as
    a virtual model for the admin UI.
    """
    await _check_staff(request)
    
    metadata = {}
    for model, model_admin in admin_site._registry.items():
        table_name = str(getattr(model, "__tablename__", model.__name__.lower()))
        
        # Introspect fields
        fields = await _get_fields_data(model, model_admin)
        
        # Introspect inlines
        inlines = []
        for inline_cls in model_admin.inlines:
            inline = inline_cls()
            inline_table = str(getattr(inline.model, "__tablename__", inline.model.__name__.lower()))
            inlines.append({
                "model": inline.model.__name__,
                "table": inline_table,
                "fields": inline.get_form_fields(),
                "template": getattr(inline, "template", "tabular"),
                "extra": getattr(inline, "extra", 3)
            })
        
        metadata[table_name] = {
            "name": model.__name__,
            "verbose_name": model_admin.get_verbose_name(model),
            "verbose_name_plural": model_admin.get_verbose_name_plural(model),
            "label": model_admin.get_verbose_name(model),  # Compatibility with SPA
            "label_plural": model_admin.get_verbose_name_plural(model), # Compatibility with SPA
            "table": table_name,
            "slug": model_admin.get_slug(model),
            "icon": getattr(model_admin, "icon", "fa-solid fa-cube"),
            "fields": fields,
            "list_display": model_admin.get_list_display(model),
            "search_fields": model_admin.search_fields,
            "list_filter": model_admin.list_filter,
            "actions": [a.name if hasattr(a, 'name') else str(a) for a in model_admin.actions],
            "inlines": inlines
        }
    
    # Add feature flags as a virtual model
    metadata["flags"] = {
        "name": "FeatureFlag",
        "verbose_name": "Feature Flag",
        "verbose_name_plural": "Feature Flags",
        "label": "Feature Flag",
        "label_plural": "Feature Flags",
        "table": "flags",
        "slug": "flags",
        "icon": "fa-solid fa-flag",
        "is_virtual": True,
        "fields": [
            {"key": "id", "name": "id", "type": "string", "label": "ID", "readonly": True},
            {"key": "name", "name": "name", "type": "string", "label": "Flag Name", "required": True},
            {"key": "description", "name": "description", "type": "text", "label": "Description", "required": False},
            {"key": "strategy", "name": "strategy", "type": "select", "label": "Strategy", "required": True, "choices": ["always_on", "always_off", "percentage", "user_id", "user_segment", "tenant_id", "environment"]},
            {"key": "percentage", "name": "percentage", "type": "integer", "label": "Percentage", "required": False},
            {"key": "enabled", "name": "enabled", "type": "boolean", "label": "Enabled", "required": True},
            {"key": "created_at", "name": "created_at", "type": "datetime", "label": "Created", "readonly": True},
            {"key": "updated_at", "name": "updated_at", "type": "datetime", "label": "Updated", "readonly": True},
            {"key": "usage_count", "name": "usage_count", "type": "integer", "label": "Usage Count", "readonly": True}
        ],
        "list_display": ["name", "strategy", "enabled", "usage_count", "updated_at"],
        "search_fields": ["name", "description"],
        "list_filter": ["strategy", "enabled"],
        "actions": [],
        "inlines": []
    }
        
    return JsonResponse(metadata)


async def admin_api_list(
    request: Request, model: type, model_admin: Any
) -> JsonResponse:
    """Generic JSON list view with support for search, filtering, and sorting."""
    await _check_staff(request)
    
    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 20))
    search = request.query_params.get("q", "")
    order_by = request.query_params.get("order_by", "")
    
    session = getattr(request.state, "db", None) or getattr(request.app.state, "db", None)
    from eden.db import _MISSING
    qs = model.query(session or _MISSING)
    
    # Bypass tenancy for admin list view
    if hasattr(qs, "include_tenantless"):
        qs = qs.include_tenantless()
    
    # ── Search ────────────────────────────────────────────────────────
    if search and model_admin.search_fields:
        from eden.db import Q
        conditions = []
        for field_name in model_admin.search_fields:
            conditions.append(Q(**{f"{field_name}__icontains": search}))
        if conditions:
            combined_q = conditions[0]
            for q in conditions[1:]:
                combined_q |= q
            qs = qs.filter(combined_q)
            
    # ── Filtering ─────────────────────────────────────────────────────
    for filter_field in model_admin.list_filter:
        val = request.query_params.get(filter_field)
        if val is not None and val != "":
            # Basic equality filter, can be expanded for ranges/choices
            kwargs = {filter_field: val}
            if val.lower() == "true": kwargs[filter_field] = True
            elif val.lower() == "false": kwargs[filter_field] = False
            qs = qs.filter_by(**kwargs)
            
    # ── Ordering ──────────────────────────────────────────────────────
    if order_by:
        # Support multiple fields separated by comma
        fields = order_by.split(",")
        qs = qs.order_by(*fields)
    else:
        qs = qs.order_by(*model_admin.ordering)
    
    # Pagination
    page_obj = await qs.paginate(page, per_page)
    
    # Convert records to dicts
    serialized_records = []
    list_display = model_admin.get_list_display(model)
    
    for record in page_obj.items:
        record_dict = {}
        # Serialize both columns and other list_display items (properties, methods)
        for f in list_display:
            val = getattr(record, f, None)
            if callable(val):
                try: val = val()
                except: val = str(val)
                
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            elif isinstance(val, (uuid.UUID, bytes)):
                val = str(val)
            elif hasattr(val, "id"): # Handle model instances
                val = str(val.id)
                
            record_dict[f] = val
            
        # Ensure ID is always present for SPA row identification
        if "id" not in record_dict and hasattr(record, "id"):
            record_dict["id"] = str(record.id)
            
        serialized_records.append(record_dict)
        
    return JsonResponse({
        "items": serialized_records,
        "total": page_obj.total,
        "page": page,
        "total_pages": page_obj.total_pages,
        "per_page": per_page
    })


async def admin_api_action(
    request: Request, model: type, model_admin: Any
) -> JsonResponse:
    """Execute a bulk action on multiple records."""
    await _check_staff(request)
    
    data = await request.json()
    action_name = data.get("action")
    ids = data.get("ids", [])
    
    if not action_name or not ids:
        return JsonResponse({"error": "Missing action or ids"}, status_code=400)
        
    if action_name not in model_admin.actions:
        return JsonResponse({"error": f"Action '{action_name}' not available"}, status_code=400)
        
    session = getattr(request.state, "db", None) or getattr(request.app.state, "db", None)
    from eden.db import _MISSING
    
    # Built-in: delete_selected
    if action_name == "delete_selected":
        count = 0
        for rid in ids:
            # Bypass tenancy for deletions via admin
            qs = model.query(session or _MISSING)
            if hasattr(qs, "include_tenantless"):
                qs = qs.include_tenantless()
            record = await qs.filter(id=rid).first()
            if record:
                await model_admin.delete_model(request, record)
                count += 1
        return JsonResponse({"status": "ok", "message": f"Deleted {count} records"})
        
    # Custom actions
    action_func = getattr(model_admin, action_name, None)
    if action_func and callable(action_func):
        try:
            # Query objects - Bypass tenancy
            qs = model.query(session or _MISSING).filter(model.id.in_(ids))
            if hasattr(qs, "include_tenantless"):
                qs = qs.include_tenantless()
            objects = await qs.all()
            result = await action_func(request, objects)
            return JsonResponse({"status": "ok", "message": result or "Action executed successfully"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status_code=500)
            
    return JsonResponse({"error": f"Action function for '{action_name}' not found"}, status_code=500)


async def admin_api_get(
    request: Request, model: type, model_admin: Any, record_id: str
) -> JsonResponse:
    """Get a single record as JSON."""
    await _check_staff(request)
    
    session = getattr(request.state, "db", None) or getattr(request.app.state, "db", None)
    from eden.db import _MISSING
    
    qs = model.query(session or _MISSING)
    if hasattr(qs, "include_tenantless"):
        qs = qs.include_tenantless()
        
    record = await qs.filter(id=record_id).first()
    if not record:
        return JsonResponse({"error": "Not found"}, status_code=404)
        
    # Serialization
    from sqlalchemy import inspect as sa_inspect
    mapper = sa_inspect(model)
    record_dict = {}
    
    # Prioritize fields defined in ModelAdmin
    fields = model_admin.get_fields(model).keys() or [col.key for col in mapper.columns]
    
    for f in fields:
        val = getattr(record, f, None)
        if callable(val):
            try: val = val()
            except: val = str(val)
            
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        elif isinstance(val, (uuid.UUID, bytes)):
            val = str(val)
        elif hasattr(val, "id"):
            val = str(val.id)
        record_dict[f] = val
        
    return JsonResponse(record_dict)


async def admin_api_create(
    request: Request, model: type, model_admin: Any
) -> JsonResponse:
    session = getattr(request.state, "db", None) or getattr(request.app.state, "db", None)
    from eden.db import _MISSING
    
    try:
        data = await request.json()
        instance = model()
        
        # Use BaseForm for validation if available
        from eden.forms import BaseForm
        try:
            form = BaseForm.from_model(instance)
            form.data = data
            if not form.is_valid():
                return JsonResponse({"error": "Validation failed", "fields": form.errors}, status_code=400)
            # Update instance with validated data
            for key, val in form.model_instance.model_dump(exclude_unset=True).items():
                setattr(instance, key, val)
        except Exception as e:
            # Fallback to direct mapping if form logic fails
            from sqlalchemy import inspect as sa_inspect
            mapper = sa_inspect(model)
            for col in mapper.columns:
                if col.key in data and col.key not in model_admin.exclude_fields:
                    setattr(instance, col.key, data[col.key])
                
        await model_admin.save_model(request, instance, data, change=False)
        
        # Log action
        user = getattr(request.state, "user", None)
        try:
            from eden.admin.models import AuditLog
            await AuditLog.log(
                user_id=str(user.id) if user else None,
                action="create",
                model=model,
                record_id=str(getattr(instance, "id", "new"))
            )
        except Exception:
            pass
            
        return JsonResponse({"status": "ok", "id": str(getattr(instance, "id", "new"))})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status_code=400)


async def admin_api_update(
    request: Request, model: type, model_admin: Any, record_id: str
) -> JsonResponse:
    """Update a record via JSON."""
    await _check_staff(request)
    
    session = getattr(request.state, "db", None) or getattr(request.app.state, "db", None)
    from eden.db import _MISSING
    
    qs = model.query(session or _MISSING)
    if hasattr(qs, "include_tenantless"):
        qs = qs.include_tenantless()
    record = await qs.filter(id=record_id).first()
    
    if not record:
        return JsonResponse({"error": "Not found"}, status_code=404)
        
    data = await request.json()
    try:
        # Use BaseForm for validation if available
        from eden.forms import BaseForm
        try:
            form = BaseForm.from_model(record)
            form.data = data
            if not form.is_valid():
                return JsonResponse({"error": "Validation failed", "fields": form.errors}, status_code=400)
            # Update record with validated data
            for key, val in form.model_instance.model_dump(exclude_unset=True).items():
                if key not in model_admin.exclude_fields:
                    setattr(record, key, val)
        except Exception:
            # Fallback to direct mapping
            from sqlalchemy import inspect as sa_inspect
            mapper = sa_inspect(model)
            for col in mapper.columns:
                if col.key in data and col.key not in model_admin.exclude_fields:
                    setattr(record, col.key, data[col.key])
                
        await model_admin.save_model(request, record, data, change=True)
        
        # Log action
        user = getattr(request.state, "user", None)
        try:
            from eden.admin.models import AuditLog
            await AuditLog.log(
                user_id=str(user.id) if user else None,
                action="update",
                model=model,
                record_id=str(record_id)
            )
        except Exception:
            pass
            
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status_code=400)


async def admin_api_delete(
    request: Request, model: type, model_admin: Any, record_id: str
) -> JsonResponse:
    """Delete a record via JSON."""
    await _check_staff(request)
    
    session = getattr(request.state, "db", None) or getattr(request.app.state, "db", None)
    from eden.db import _MISSING
    
    qs = model.query(session or _MISSING)
    if hasattr(qs, "include_tenantless"):
        qs = qs.include_tenantless()
    record = await qs.filter(id=record_id).first()
    
    if not record:
        return JsonResponse({"error": "Not found"}, status_code=404)
        
    try:
        await model_admin.delete_model(request, record)
        
        # Log action
        user = getattr(request.state, "user", None)
        try:
            from eden.admin.models import AuditLog
            await AuditLog.log(
                user_id=str(user.id) if user else None,
                action="delete",
                model=model,
                record_id=str(record_id)
            )
        except Exception:
            pass
            
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status_code=400)


# ── Helper Utilities ──────────────────────────────────────────────────

async def _get_fields_data(model: type, model_admin: Any, instance: Any | None = None) -> list[dict[str, Any]]:
    """Introspect model fields for form generation."""
    from sqlalchemy import inspect as sa_inspect
    mapper = sa_inspect(model)
    fields_data = []
    
    for col in mapper.columns:
        if col.key in model_admin.exclude_fields and not (instance and col.key == "id"):
            continue
            
        value = getattr(instance, col.key, "") if instance else ""
        
        # Serialization for JSON/UUID/Date
        if value is not None:
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            elif isinstance(value, (uuid.UUID, bytes)):
                value = str(value)
            elif hasattr(value, "id"):
                value = str(value.id)

        field_info = {}
        if hasattr(model, col.key):
            attr = getattr(model, col.key)
            if hasattr(attr, "info"):
                field_info = attr.info
        
        # Detect encrypted fields
        is_encrypted = field_info.get("encrypted", False)
        widget = field_info.get("widget")
        if is_encrypted and not widget:
            widget = "password"

        # Detect choices
        choices = field_info.get("choices")
        if not choices and hasattr(col.type, "enums"): # For Enum types
            choices = list(col.type.enums)

        fields_data.append({
            "key": col.key,
            "label": field_info.get("label", col.key.replace("_", " ").title()),
            "value": value if not is_encrypted else "********",
            "widget": widget,
            "required": not getattr(col, "nullable", True),
            "readonly": col.key in model_admin.readonly_fields or col.key == "id",
            "type": str(col.type).split("(")[0].lower(), # simplify type (e.g. varchar, integer)
            "is_encrypted": is_encrypted,
            "choices": choices
        })
    return fields_data


async def _get_inlines_data(model: type, model_admin: Any, instance: Any | None = None) -> list[dict[str, Any]]:
    """Prepare inline formsets (Tabular/Stacked) with full data."""
    from eden.admin.inline import prepare_inline_data
    
    if not instance:
        # For add view, return empty inlines
        inlines_data = []
        if hasattr(model_admin, "inlines"):
            for inline_class in model_admin.inlines:
                inline = inline_class()
                child_model = inline.model
                fields = inline.get_form_fields() if hasattr(inline, 'get_form_fields') else []
                
                # Add blank rows for new related objects
                rows = []
                for _ in range(getattr(inline, "extra", 1)):
                    row_fields = []
                    for field_name in fields:
                        row_fields.append({
                            "name": field_name,
                            "label": field_name.replace("_", " ").title(),
                            "value": ""
                        })
                    rows.append(row_fields)
                
                inlines_data.append({
                    "model_name": child_model.__name__,
                    "template": getattr(inline, "template", "tabular_inline"),
                    "rows": rows,
                    "fields": fields
                })
        return inlines_data
    
    # For edit view with instance, fetch related data
    return await prepare_inline_data(model_admin, instance, model)

