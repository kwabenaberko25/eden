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


async def admin_dashboard(request: Request, admin_site: Any) -> HtmlResponse:
    """
    Render the admin dashboard with registered model counts.
    
    Args:
        request: The HTTP request.
        admin_site: The AdminSite instance with registered models.
    
    Returns:
        HtmlResponse: Rendered dashboard HTML.
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
            "url": f"/{model.__tablename__}/",
        })

    html = _render_dashboard(models_info)
    return HtmlResponse(html)


async def admin_list_view(
    request: Request, model: type, model_admin: Any
) -> HtmlResponse:
    """Paginated list view for a model."""
    await _check_staff(request)

    session = getattr(request.state, "db", None)
    from eden.db import _MISSING
    qs = model.query(session or _MISSING)

    page = int(request.query_params.get("page", 1))
    search = request.query_params.get("q", "").strip()
    per_page = model_admin.per_page

    # Search
    if search and model_admin.search_fields:
        from eden.db import Q
        conditions = []
        for field_name in model_admin.search_fields:
            conditions.append(Q(**{f"{field_name}__icontains": search}))
        if conditions:
            # Combine multiple search fields with OR
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

    columns = model_admin.get_list_display(model)
    model_name = model_admin.get_verbose_name_plural(model)

    html = _render_list(
        model_name=model_name,
        table_name=model.__tablename__,
        columns=columns,
        records=records,
        page=page,
        total_pages=total_pages,
        total=total,
        search=search,
    )
    return HtmlResponse(html)


async def admin_detail_view(
    request: Request, model: type, model_admin: Any, record_id: str
) -> HtmlResponse:
    """Detail view for a single record with rich field rendering."""
    await _check_staff(request)

    session = getattr(request.state, "db", None)
    from eden.db import _MISSING
    record = await model.get(session or _MISSING, record_id)
    if not record:
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
    csrf_token = get_csrf_token(request)
    
    html = _render_detail(
        model_name=model_name,
        table_name=model.__tablename__,
        record_id=str(record.id),
        fields=fields_data,
        csrf_token=csrf_token,
    )
    return HtmlResponse(html)


async def admin_add_view(
    request: Request, model: type, model_admin: Any
) -> Response:
    """View to create a new record."""
    await _check_staff(request)
    csrf_token = get_csrf_token(request)
    
    if request.method == "POST":
        form_data = await request.form()
        try:
            instance = model()
            # Process fields
            from sqlalchemy import inspect as sa_inspect
            mapper = sa_inspect(model)
            for col in mapper.columns:
                if col.key in form_data and col.key not in model_admin.exclude_fields:
                    val = form_data[col.key]
                    if str(col.type) == "BOOLEAN":
                        val = val.lower() == "on"
                    setattr(instance, col.key, val)
            
            await model_admin.save_model(request, instance, form_data, change=False)
            
            # Log action
            user = getattr(request.state, "user", None)
            from eden.admin.models import AuditLog
            await AuditLog.log(
                user_id=str(user.id) if user else None,
                action="create",
                model=model,
                record_id=str(instance.id)
            )
            
            return RedirectResponse(url=f"/admin/{model.__tablename__}/", status_code=303)
        except Exception as e:
            return HtmlResponse(_render_form(
                model_name=model_admin.get_verbose_name(model),
                table_name=model.__tablename__,
                fields=await _get_fields_data(model, model_admin),
                csrf_token=csrf_token,
                error=str(e),
                is_add=True,
                inlines=await _get_inlines_data(model, model_admin)
            ))

    # GET request
    fields_data = await _get_fields_data(model, model_admin)
    html = _render_form(
        model_name=model_admin.get_verbose_name(model),
        table_name=model.__tablename__,
        fields=fields_data,
        csrf_token=csrf_token,
        is_add=True,
        inlines=await _get_inlines_data(model, model_admin)
    )
    return HtmlResponse(html)


async def admin_edit_view(
    request: Request, model: type, model_admin: Any, record_id: str
) -> Response:
    """View to edit an existing record."""
    await _check_staff(request)
    csrf_token = get_csrf_token(request)
    
    session = getattr(request.state, "db", None)
    from eden.db import _MISSING
    instance = await model.get(session or _MISSING, record_id)
    if not instance:
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
                    setattr(instance, col.key, val)
            
            await model_admin.save_model(request, instance, form_data, change=True)
            
            from eden.admin.models import AuditLog
            user = getattr(request.state, "user", None)
            await AuditLog.log(
                user_id=str(user.id) if user else None,
                action="update",
                model=model,
                record_id=str(instance.id)
            )
            
            return RedirectResponse(url=f"/admin/{model.__tablename__}/", status_code=303)
        except Exception as e:
             return HtmlResponse(_render_form(
                model_name=model_admin.get_verbose_name(model),
                table_name=model.__tablename__,
                record_id=record_id,
                fields=await _get_fields_data(model, model_admin, instance),
                csrf_token=csrf_token,
                error=str(e),
                is_add=False,
                inlines=await _get_inlines_data(model, model_admin, instance)
            ))

    fields_data = await _get_fields_data(model, model_admin, instance)
    html = _render_form(
        model_name=model_admin.get_verbose_name(model),
        table_name=model.__tablename__,
        record_id=record_id,
        fields=fields_data,
        csrf_token=csrf_token,
        is_add=False,
        inlines=await _get_inlines_data(model, model_admin, instance)
    )
    return HtmlResponse(html)


async def _get_fields_data(model: Type, model_admin: Any, instance: Any | None = None) -> list[dict[str, Any]]:
    """
    Prepare field data for form rendering in templates.
    
    Args:
        model: The Model class to introspect.
        model_admin: The ModelAdmin configuration instance.
        instance: Optional model instance to populate values from.
    
    Returns:
        list[dict]: List of field dictionaries with metadata and current values.
    """
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
            "required": not col.nullable,
            "readonly": col.key in model_admin.readonly_fields or col.key == "id",
            "type": str(col.type)
        })
    return fields_data


async def _get_inlines_data(model: Type, model_admin: Any, instance: Any | None = None) -> list[dict[str, Any]]:
    """
    Prepare data for inline models in forms.
    
    Args:
        model: The Model class containing inlines.
        model_admin: The ModelAdmin configuration instance.
        instance: Optional model instance to load related records from.
    
    Returns:
        list[dict]: List of inline data dictionaries ready for rendering.
    """
    inlines_data = []
    for inline_class in model_admin.inlines:
        inline = inline_class()
        inline_model = inline.model
        
        # In a real app, we'd query for records related to 'instance'
        # For now, we'll just show the 'extra' blank rows
        fields = inline.get_form_fields()
        rows = []
        
        # If we had an instance, we would fetch related records here
        # Example: related_records = await inline_model.query(filter={...})
        
        # Add blank rows
        for _ in range(inline.extra):
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
            "template": inline.template,
            "rows": rows,
            "fields": fields
        })
    return inlines_data


async def admin_delete_view(
    request: Request, model: type, model_admin: Any, record_id: str
) -> RedirectResponse:
    """Delete a record and log the action."""
    user = getattr(request.state, "user", None)
    await _check_staff(request)

    session = getattr(request.state, "db", None)
    from eden.db import _MISSING
    
    # Audit log before delete
    await AuditLog.log(
        user_id=str(user.id) if user else None,
        action="delete",
        model=model,
        record_id=record_id
    )

    count = await model.query(session or _MISSING).filter(id=record_id).delete()
    
    if count == 0:
        raise NotFound(detail=f"Record {record_id} not found.")

    return RedirectResponse(url=f"/admin/{model.__tablename__}/", status_code=303)


async def admin_action_view(
    request: Request, model: type, model_admin: Any
) -> JsonResponse:
    """Execute bulk actions."""
    await _check_staff(request)
    data = await request.json()
    action = data.get("action")
    ids = data.get("ids", [])
    
    if action == "delete_selected":
        count = await model.query().filter(id__in=ids).delete()
        return JsonResponse({"status": "ok", "message": f"Deleted {count} records"})
    
    return JsonResponse({"status": "error", "message": "Unknown action"}, status=400)


# ── HTML Rendering Helpers ────────────────────────────────────────────

_ADMIN_CSS = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; background: #0F172A; color: #E2E8F0; }
    .admin-sidebar { width: 260px; height: 100vh; background: #1E293B; position: fixed; padding: 24px 0;
                     border-right: 1px solid #334155; }
    .admin-sidebar h1 { font-family: 'Outfit', sans-serif; font-size: 22px; padding: 0 24px 20px;
                        color: #2563EB; font-weight: 700; }
    .admin-sidebar a { display: block; padding: 10px 24px; color: #94A3B8; text-decoration: none;
                       font-size: 14px; transition: all 0.2s; }
    .admin-sidebar a:hover { background: #334155; color: #F8FAFC; }
    .admin-sidebar a.active { background: #2563EB20; color: #2563EB; border-right: 3px solid #2563EB; }
    .admin-main { margin-left: 260px; padding: 32px 40px; min-height: 100vh; position: relative; }
    .admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; position: sticky; top: -32px; background: #0F172A; z-index: 10; padding: 20px 0; }
    .admin-header h2 { font-family: 'Outfit', sans-serif; font-size: 28px; font-weight: 600; }
    .admin-card { background: rgba(30,41,59,0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
                  border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; margin-bottom: 16px;
                  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
    .admin-card:hover { border-color: #2563EB60; transform: translateY(-2px) scale(1.01);
                        box-shadow: 0 10px 30px rgba(0,0,0,0.3), 0 0 20px rgba(37,99,235,0.1); }
    .admin-table { width: 100%; border-collapse: collapse; }
    .admin-table th { text-align: left; padding: 12px 16px; font-size: 12px; text-transform: uppercase;
                      letter-spacing: 0.05em; color: #64748B; border-bottom: 1px solid #334155; }
    .admin-table td { padding: 12px 16px; border-bottom: 1px solid #1E293B; font-size: 14px; }
    .admin-table tr:hover { background: #1E293B; }
    .admin-btn { display: inline-block; padding: 8px 20px; border-radius: 8px; font-size: 14px;
                 font-weight: 500; text-decoration: none; cursor: pointer; border: none;
                 transition: all 0.2s; }
    .admin-btn-primary { background: #2563EB; color: white; }
    .admin-btn-primary:hover { background: #1D4ED8; transform: translateY(-1px); }
    .admin-btn-danger { background: #DC2626; color: white; }
    .admin-btn-danger:hover { background: #B91C1C; }
    .admin-btn-ghost { background: transparent; color: #94A3B8; border: 1px solid #334155; }
    .admin-btn-ghost:hover { border-color: #64748B; color: #E2E8F0; }
    .admin-search { display: flex; gap: 8px; }
    .admin-search input { background: #0F172A; border: 1px solid #334155; border-radius: 8px;
                          padding: 8px 16px; color: #E2E8F0; font-size: 14px; width: 300px;
                          transition: border-color 0.2s; }
    .admin-search input:focus { outline: none; border-color: #2563EB; }
    .admin-pagination { display: flex; gap: 8px; align-items: center; justify-content: center;
                        margin-top: 20px; }
    .admin-stat { text-align: center; }
    .admin-stat .number { font-size: 32px; font-weight: 700; color: #F8FAFC; }
    .admin-stat .label { font-size: 12px; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; }
    .admin-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
    .field-row { display: flex; border-bottom: 1px solid #1E293B; padding: 12px 0; }
    .field-label { width: 200px; color: #64748B; font-size: 13px; text-transform: uppercase;
                   letter-spacing: 0.05em; flex-shrink: 0; }
    .field-value { color: #E2E8F0; font-size: 14px; word-break: break-all; }
</style>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
"""


def _render_dashboard(models_info: list[dict]) -> str:
    cards_html = ""
    for m in models_info:
        cards_html += f"""
        <a href="/admin{m['url']}" style="text-decoration: none;">
        <div class="admin-card">
            <div class="admin-stat">
                <div class="number">{m['count']}</div>
                <div class="label">{m['name_plural']}</div>
            </div>
        </div>
        </a>
        """

    return f"""<!DOCTYPE html>
<html lang="en"><head><title>Eden Admin</title>{_ADMIN_CSS}</head>
<body>
<div class="admin-sidebar">
    <h1>🌿 Eden Admin</h1>
    <a href="/admin/" class="active">Dashboard</a>
    {''.join(f'<a href="/admin{m["url"]}">{m["name_plural"]}</a>' for m in models_info)}
</div>
<div class="admin-main">
    <div class="admin-header"><h2>Dashboard</h2></div>
    <div class="admin-grid">{cards_html}</div>
</div>
</body></html>"""


def _render_list(
    model_name, table_name, columns, records, page, total_pages, total, search
) -> str:
    header_html = "<th><input type='checkbox' onclick='toggleAll(this)'></th>"
    header_html += "".join(f"<th>{col.replace('_', ' ').title()}</th>" for col in columns)
    header_html += "<th>Actions</th>"

    rows_html = ""
    for record in records:
        rid = str(record.id)
        cells = f"<td><input type='checkbox' name='selected_ids' value='{rid}'></td>"
        for col in columns:
            val = getattr(record, col, "")
            cells += f"<td>{_render_value(val)}</td>"
        
        cells += f'<td><a href="/admin/{table_name}/{rid}" class="admin-btn admin-btn-ghost" style="padding:4px 12px;font-size:12px;">View</a></td>'
        rows_html += f"<tr>{cells}</tr>"

    pagination = ""
    if total_pages > 1:
        pages = ""
        # Simple pagination buttons
        for p in range(max(1, page-2), min(total_pages+1, page+3)):
            active = "admin-btn-primary" if p == page else "admin-btn-ghost"
            pages += f'<a href="/admin/{table_name}/?page={p}&q={search}" class="admin-btn {active}" style="padding:4px 12px;">{p}</a>'
        pagination = f'<div class="admin-pagination">{pages}</div>'

    return f"""<!DOCTYPE html>
<html lang="en"><head><title>{model_name} — Eden Admin</title>{_ADMIN_CSS}
<script>
    function toggleAll(source) {{
        checkboxes = document.getElementsByName('selected_ids');
        for(var i=0, n=checkboxes.length;i<n;i++) {{
            checkboxes[i].checked = source.checked;
        }}
    }}
</script>
</head>
<body>
<div class="admin-sidebar">
    <h1>🌿 Eden Admin</h1>
    <a href="/admin/">Dashboard</a>
    <a href="/admin/{table_name}/" class="active">{model_name}</a>
</div>
<div class="admin-main">
    <div class="admin-header">
        <h2>{model_name} <span style="color:#64748B;font-size:16px;">({total})</span></h2>
        <div style="display:flex; gap:16px;">
            <div class="admin-search">
                <form method="get">
                    <input type="text" name="q" placeholder="Search..." value="{search}">
                </form>
            </div>
            <a href="/admin/{table_name}/add" class="admin-btn admin-btn-primary">+ Add {model_name.rstrip('s')}</a>
            <button class="admin-btn admin-btn-danger" onclick="executeAction('delete_selected')">Delete Selected</button>
        </div>
    </div>
    <div class="admin-card" style="padding:0;overflow:hidden;">
        <table class="admin-table">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    {pagination}
</div>
<script>
    async def executeAction(action) {{
        const ids = Array.from(document.getElementsByName('selected_ids'))
            .filter(i => i.checked).map(i => i.value);
        if(!ids.length) return alert('Select items first');
        if(!confirm('Apply ' + action + ' to ' + ids.length + ' items?')) return;
        
        const resp = await fetch('/admin/{table_name}/action', {{
            method: 'POST',
            body: JSON.stringify({{action, ids}}),
            headers: {{'Content-Type': 'application/json'}}
        }});
        if(resp.ok) window.location.reload();
        else alert('Error: ' + (await resp.json()).message);
    }}
</script>
</body></html>"""


def _render_detail(model_name, table_name, record_id, fields, csrf_token="") -> str:
    fields_html = ""
    for field in fields:
        fields_html += f"""
        <div class="field-row">
            <div class="field-label">{field['label']}</div>
            <div class="field-value">{_render_widget(field)}</div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en"><head><title>{model_name} Detail — Eden Admin</title>{_ADMIN_CSS}</head>
<body>
<div class="admin-sidebar">
    <h1>🌿 Eden Admin</h1>
    <a href="/admin/">Dashboard</a>
    <a href="/admin/{table_name}/" class="active">{model_name}</a>
</div>
<div class="admin-main">
    <div class="admin-header">
        <h2>{model_name} Detail</h2>
        <div>
            <a href="/admin/{table_name}/" class="admin-btn admin-btn-ghost">← Back to List</a>
            <form method="post" action="/admin/{table_name}/{record_id}/delete" style="display:inline;">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                <button type="submit" class="admin-btn admin-btn-danger"
                        onclick="return confirm('Delete this record?')">Delete</button>
            </form>
        </div>
    </div>
    <div class="admin-card">
        {fields_html}
    </div>
</div>
</body></html>"""


def _render_value(val: Any) -> str:
    """Format simple values for list view."""
    if val is True:
        return "<span style='color:#22C55E'>▲ Yes</span>"
    if val is False:
        return "<span style='color:#EF4444'>▼ No</span>"
    if val is None:
        return "<i style='color:#64748B'>null</i>"
    
    from datetime import datetime
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M")
        
    return _truncate(str(val))


def _render_widget(field: dict) -> str:
    """Render rich detail view widgets."""
    val = field["value"]
    widget = field.get("widget")
    
    # Check if widget is a FieldWidget instance and use its render method
    from eden.admin.widgets import FieldWidget
    if isinstance(widget, FieldWidget):
        try:
            return widget.render(val)
        except Exception as e:
            return f"<span style='color:red'>Error rendering widget: {e}</span>"

    if widget == "file" and val:
        return f'<a href="{val}" target="_blank" style="color:#2563EB">📂 {val}</a>'
    
    if isinstance(val, bool):
        color = "#22C55E" if val else "#EF4444"
        text = "YES" if val else "NO"
        return f'<span style="background:{color}20; color:{color}; padding:2px 8px; border-radius:4px; font-weight:600; font-size:12px;">{text}</span>'
    
    from datetime import datetime
    if isinstance(val, datetime):
        return f"<div style='color:#F8FAFC;font-family:monospace;'>{val.isoformat()}</div>"
        
    if field.get("type", "").lower() == "json":
        import json
        try:
            formatted = json.dumps(val, indent=2)
            return f"<pre style='background:#0F172A; padding:12px; border-radius:8px; border:1px solid #334155; overflow:auto;'>{formatted}</pre>"
        except: pass
        
    return _truncate(str(val), 500)


def _truncate(text: str, max_len: int = 80) -> str:
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text


def _render_form(model_name, table_name, fields, record_id=None, csrf_token="", error=None, is_add=False, inlines=None) -> str:
    title = f"Add {model_name}" if is_add else f"Edit {model_name}"
    action_url = f"/admin/{table_name}/add" if is_add else f"/admin/{table_name}/{record_id}/edit"
    
    inlines = inlines or []
    inlines_html = ""
    for inline in inlines:
        rows_html = ""
        if inline['template'] == "tabular_inline":
            header_html = "".join([f"<th style='padding:12px; border-bottom:1px solid #334155; text-align:left;'>{f}</th>" for f in inline['fields']])
            for row in inline['rows']:
                cols_html = "".join([f"<td style='padding:8px 12px; border-bottom:1px solid #1E293B;'><input type='text' name='inline_{inline['model_name']}_{f['name']}' value='{f['value']}' class='admin-input' style='background:transparent; border:none; padding:4px;'></td>" for f in row])
                rows_html += f"<tr>{cols_html}</tr>"
            
            inlines_html += f"""
            <div class="admin-card" style="margin-top:24px; padding:0; overflow:hidden;">
                <div style="background:#1E293B; padding:12px 20px; font-weight:600; border-bottom:1px solid #334155;">{inline['model_name']}s</div>
                <table style="width:100%; border-collapse:collapse;">
                    <thead><tr>{header_html}</tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
            """
        else: # stacked_inline
             for i, row in enumerate(inline['rows']):
                fields_html = "".join([f"<div style='margin-bottom:12px;'><label style='display:block; font-size:12px; color:#94A3B8; margin-bottom:4px;'>{f['label']}</label><input type='text' name='inline_{inline['model_name']}_{f['name']}_{i}' value='{f['value']}' class='admin-input'></div>" for f in row])
                rows_html += f"<div style='padding:16px; border-bottom:1px solid #334155;'>{fields_html}</div>"
             
             inlines_html += f"""
             <div class="admin-card" style="margin-top:24px; padding:0;">
                <div style="background:#1E293B; padding:12px 20px; font-weight:600; border-bottom:1px solid #334155;">{inline['model_name']}s</div>
                {rows_html}
             </div>
             """

    fields_html = ""
    for field in fields:
        readonly = "readonly style='background:#1E293B20; color:#64748B; cursor:not-allowed;'" if field.get('readonly') else ""
        required = "required" if field.get('required') and not is_add else ""
        
        widget_html = ""
        from eden.admin.widgets import FieldWidget
        widget = field.get("widget")
        
        if isinstance(widget, FieldWidget):
            try:
                widget_html = widget.render(field['key'], field['value'])
            except Exception as e:
                widget_html = f"<div class='text-red-500'>Error rendering widget: {e}</div>"
        else:
            if field['type'] == "BOOLEAN":
                checked = "checked" if field['value'] else ""
                widget_html = f'<input type="checkbox" name="{field["key"]}" {checked} class="admin-checkbox">'
            else:
                 widget_html = f'<input type="text" name="{field["key"]}" value="{field["value"]}" class="admin-input" {readonly} {required}>'

        fields_html += f"""
        <div class="field-row" style="flex-direction: column; align-items: flex-start; gap: 8px; border-bottom: 1px solid #1E293B; padding: 16px 0;">
            <label class="field-label" style="width: auto; font-weight: 600; font-size: 14px; color: #94A3B8;">{field['label']}</label>
            <div style="width: 100%;">
                {widget_html}
            </div>
        </div>
        """

    error_banner = f'<div style="background:#EF444420; color:#EF4444; padding:12px; border-radius:8px; border:1px solid #EF444440; margin-bottom:20px;">{error}</div>' if error else ""

    return f"""<!DOCTYPE html>
<html lang="en"><head><title>{title} — Eden Admin</title>
{_ADMIN_CSS}
<style>
    .admin-input {{ width: 100%; background: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 10px 16px; color: #E2E8F0; font-size: 14px; transition: border-color 0.2s; }}
    .admin-input:focus {{ outline: none; border-color: #2563EB; }}
    .admin-checkbox {{ width: 18px; height: 18px; border-radius: 4px; border: 1px solid #334155; accent-color: #2563EB; }}
    .field-row:last-child {{ border-bottom: none; }}
</style>
</head>
<body>
<div class="admin-sidebar">
    <h1>🌿 Eden Admin</h1>
    <a href="/admin/">Dashboard</a>
    <a href="/admin/{table_name}/" class="active">{model_name}</a>
</div>
<div class="admin-main">
    <div class="admin-header">
        <h2>{title}</h2>
        <div>
            <a href="/admin/{table_name}/" class="admin-btn admin-btn-ghost">Cancel</a>
        </div>
    </div>
    {error_banner}
    <div class="admin-card">
        <form method="post" action="{action_url}">
            <input type="hidden" name="csrf_token" value="{csrf_token}">
            {fields_html}
            {inlines_html}
            <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #334155; display: flex; gap: 12px;">
                <button type="submit" class="admin-btn admin-btn-primary">Save {model_name}</button>
            </div>
        </form>
    </div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/loader.min.js"></script>
<script>
    require.config({{ paths: {{ vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' }} }});
    require(['vs/editor/editor.main'], function () {{
        const containers = document.querySelectorAll('.monaco-editor-instance');
        containers.forEach(container => {{
            const name = container.dataset.name;
            const language = container.dataset.language;
            const textarea = document.getElementById('textarea_' + name);
            const editor = monaco.editor.create(container, {{
                value: textarea.value,
                language: language,
                theme: 'vs-dark',
                automaticLayout: true,
                minimap: {{ enabled: false }},
                fontSize: 14
            }});
            editor.onDidChangeModelContent(() => {{
                textarea.value = editor.getValue();
            }});
        }});
    }});
</script>
</body></html>"""


async def admin_login(request: Request, admin_site: Any) -> Response:
    """Handle admin login."""
    error = None
    next_url = request.query_params.get("next", "/admin/")
    csrf_token = get_csrf_token(request)

    if request.method == "POST":
        form_data = await request.form()
        email = form_data.get("email")
        password = form_data.get("password")

        from eden.auth import authenticate
        user = await authenticate(email, password)

        if user:
            if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
                from eden.auth import login
                await login(request, user)
                return RedirectResponse(url=next_url, status_code=303)
            else:
                error = "Access denied: Staff status required."
        else:
            error = "Invalid email or password."

    return HtmlResponse(_render_login(csrf_token, error, next_url))


def _render_login(csrf_token, error=None, next_url="/admin/") -> str:
    error_banner = f'<div style="background:#EF444420; color:#EF4444; padding:12px; border-radius:8px; border:1px solid #EF444440; margin-bottom:20px; font-size:14px;">{error}</div>' if error else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Login | Eden Admin</title>
    {_ADMIN_CSS}
    <style>
        body {{ display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #0F172A; }}
        .login-card {{ width: 100%; max-width: 400px; padding: 40px; background: #1E293B; border-radius: 16px; border: 1px solid #334155; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); }}
        .login-card h1 {{ font-family: 'Outfit', sans-serif; font-size: 24px; color: #F8FAFC; text-align: center; margin-bottom: 8px; }}
        .login-card p {{ color: #94A3B8; text-align: center; font-size: 14px; margin-bottom: 32px; }}
        .form-group {{ margin-bottom: 20px; }}
        .form-group label {{ display: block; font-size: 12px; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }}
        .form-input {{ width: 100%; background: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px; color: #E2E8F0; font-size: 14px; transition: border-color 0.2s; }}
        .form-input:focus {{ outline: none; border-color: #2563EB; }}
        .login-btn {{ width: 100%; background: #2563EB; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: background 0.2s; margin-top: 8px; }}
        .login-btn:hover {{ background: #1D4ED8; }}
    </style>
</head>
<body>
    <div class="login-card">
        <h1>🌿 Eden Admin</h1>
        <p>Sign in to your administrative account</p>
        
        {error_banner}

        <form method="post">
            <input type="hidden" name="csrf_token" value="{csrf_token}">
            <div class="form-group">
                <label>Email Address</label>
                <input type="email" name="email" class="form-input" required placeholder="name@example.com" autofocus>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" class="form-input" required placeholder="••••••••">
            </div>
            <button type="submit" class="login-btn">Sign In</button>
        </form>
    </div>
</body>
</html>"""
