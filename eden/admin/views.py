"""
Eden — Admin Panel Views

Auto-generated CRUD views for registered models.
"""

import math
from typing import Any, Type

from eden.exceptions import Forbidden, NotFound
from eden.requests import Request
from eden.responses import HtmlResponse, RedirectResponse, JsonResponse, Response
from eden.middleware import get_csrf_token
from eden.admin.models import AuditLog


async def _check_staff(request: Request) -> None:
    """
    Ensure the user is authenticated and has staff privileges.
    
    Raises:
        Forbidden: If user is not authenticated or lacks staff permission.
    
    Returns:
        None
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise Forbidden(detail="Authentication required to access admin.")
    if not getattr(user, "is_staff", False) and not getattr(user, "is_superuser", False):
        raise Forbidden(detail="Staff access required.")


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


async def _get_model_count(model_name: str) -> int:
    """Helper to get count of a model by name safely."""
    try:
        from eden.db import Model
        # This is a bit dynamic, normally we'd import the model directly
        # But for the dashboard we can be more flexible
        for subclass in Model.__subclasses__():
            if subclass.__name__ == model_name:
                return await subclass.count()
    except Exception:
        pass
    return 0


async def admin_list_view(
    request: Request, model: type, model_admin: Any, admin_site: Any
) -> Response:
    """Paginated list view for a model."""
    await _check_staff(request)

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
            
            # Save inlines
            if hasattr(model_admin, "inlines"):
                for inline_cls in model_admin.inlines:
                    inline = inline_cls()
                    inline_model = inline.model
                    # Parse form data for this inline
                    # Format: inline_{model_name}_{index}_{field_name}
                    for key in form_data:
                        if key.startswith(f"inline_{inline_model.__name__}_"):
                            parts = key.split("_")
                            if len(parts) >= 4:
                                # index = parts[2]
                                field_name = parts[3]
                                # This is a bit simplified, usually we'd group by index
                                # For now, handles single 'extra' row well
                                val = form_data[key]
                                if val:
                                    inline_instance = inline_model()
                                    # Set foreign key (assuming 'ticket_id' or similar, but need generic way)
                                    # For SupportTicket -> TicketMessage, it's 'ticket_id'
                                    fk_name = str(getattr(model, "__tablename__", model.__name__.lower())).rstrip("s") + "_id"
                                    if hasattr(inline_instance, fk_name):
                                        setattr(inline_instance, fk_name, instance.id)
                                    elif hasattr(inline_instance, "ticket_id") and model.__name__ == "SupportTicket":
                                        setattr(inline_instance, "ticket_id", instance.id)
                                    
                                    setattr(inline_instance, field_name, val)
                                    await inline_instance.save()

            # Log action
            user = getattr(request.state, "user", None)
            try:
                from eden.admin.models import AuditLog
                await AuditLog.log(
                    user_id=str(user.id) if user else None,
                    action="create",
                    model_name=str(getattr(model, "__tablename__", model.__name__.lower())),
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
            
            # Save inlines
            if hasattr(model_admin, "inlines"):
                for inline_cls in model_admin.inlines:
                    inline = inline_cls()
                    inline_model = inline.model
                    for key in form_data:
                        if key.startswith(f"inline_{inline_model.__name__}_"):
                            parts = key.split("_")
                            if len(parts) >= 4:
                                field_name = parts[3]
                                val = form_data[key]
                                if val:
                                    inline_instance = inline_model()
                                    fk_name = str(getattr(model, "__tablename__", model.__name__.lower())).rstrip("s") + "_id"
                                    if hasattr(inline_instance, fk_name):
                                        setattr(inline_instance, fk_name, record.id)
                                    elif hasattr(inline_instance, "ticket_id") and model.__name__ == "SupportTicket":
                                        setattr(inline_instance, "ticket_id", record.id)
                                    
                                    setattr(inline_instance, field_name, val)
                                    await inline_instance.save()

            # Log action
            user = getattr(request.state, "user", None)
            try:
                from eden.admin.models import AuditLog
                await AuditLog.log(
                    user_id=str(user.id) if user else None,
                    action="update",
                    model_name=str(getattr(model, "__tablename__", model.__name__.lower())),
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
                model_name=str(getattr(model, "__tablename__", model.__name__.lower())),
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
    
    if request.method == "POST":
        form_data = await request.form()
        email = str(form_data.get("email", ""))
        password = str(form_data.get("password", ""))
        
        from eden.auth.base import authenticate
        user = await authenticate(request, email=email, password=password)
        
        if user and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
            from eden.auth.backends.session import SessionBackend
            backend = SessionBackend()
            await backend.login(request, user)
            
            from eden.responses import RedirectResponse
            return RedirectResponse(url=next_url, status_code=303)
        else:
            error = "Invalid credentials or insufficient permissions for Elite access."
            
    context = {
        "request": request,
        "error": error,
        "next_url": next_url,
    }
    return admin_site.templates.TemplateResponse(request, "login.html", context)


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
            "required": not getattr(col, "nullable", True),
            "readonly": col.key in model_admin.readonly_fields or col.key == "id",
            "type": str(col.type)
        })
    return fields_data


async def _get_inlines_data(model: type, model_admin: Any, instance: Any | None = None) -> list[dict[str, Any]]:
    """Prepare inline formsets (Tabular/Stacked)."""
    inlines_data = []
    if not hasattr(model_admin, "inlines"):
        return inlines_data
        
    for inline_class in model_admin.inlines:
        inline = inline_class()
        inline_model = inline.model
        fields = inline.get_form_fields()
        rows = []
        
        # Add blank rows for new related objects
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
            "model_name": inline_model.__name__,
            "template": getattr(inline, "template", "tabular_inline"),
            "rows": rows,
            "fields": fields
        })
    return inlines_data

