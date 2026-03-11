"""
Eden — Admin Panel Views

Auto-generated CRUD views for registered models.
"""

import math
from typing import Any

from eden.exceptions import Forbidden, NotFound
from eden.requests import Request
from eden.responses import HtmlResponse, RedirectResponse
from eden.security.csrf import get_csrf_token


async def _check_staff(request: Request) -> None:
    """Ensure the user is authenticated and is_staff."""
    user = getattr(request.state, "user", None)
    if not user:
        raise Forbidden(detail="Authentication required to access admin.")
    if not getattr(user, "is_staff", False) and not getattr(user, "is_superuser", False):
        raise Forbidden(detail="Staff access required.")


async def admin_dashboard(request: Request, admin_site: Any) -> HtmlResponse:
    """Admin dashboard showing all registered models with counts."""
    await _check_staff(request)

    models_info = []
    session = getattr(request.state, "db", None)

    for model, model_admin in admin_site._registry.items():
        # Use model.count() which supports auto-session injection
        count = await model.count()

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
    from eden.orm import _MISSING
    qs = model.query(session or _MISSING)

    page = int(request.query_params.get("page", 1))
    search = request.query_params.get("q", "").strip()
    per_page = model_admin.per_page

    # Search
    if search and model_admin.search_fields:
        from eden.orm import Q
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
    """Detail view for a single record."""
    await _check_staff(request)

    session = getattr(request.state, "db", None)
    from eden.orm import _MISSING
    record = await model.get(session or _MISSING, record_id)
    if not record:
        raise NotFound(detail=f"Record {record_id} not found.")

    from sqlalchemy import inspect as sa_inspect
    mapper = sa_inspect(model)
    fields = [(col.key, getattr(record, col.key, "")) for col in mapper.columns]

    model_name = model_admin.get_verbose_name(model)

    csrf_token = get_csrf_token(request)
    html = _render_detail(
        model_name=model_name,
        table_name=model.__tablename__,
        record_id=str(record.id),
        fields=fields,
        csrf_token=csrf_token,
    )
    return HtmlResponse(html)


async def admin_delete_view(
    request: Request, model: type, model_admin: Any, record_id: str
) -> RedirectResponse:
    """Delete a record."""
    await _check_staff(request)

    session = getattr(request.state, "db", None)
    from eden.orm import _MISSING
    
    # Use QuerySet.delete() which handles sessions and existence checks internally for bulk/filtered deletes
    # but here we use it for a single record delete by ID.
    count = await model.query(session or _MISSING).filter(id=record_id).delete()
    
    if count == 0:
        raise NotFound(detail=f"Record {record_id} not found.")

    return RedirectResponse(url=f"/admin/{model.__tablename__}/", status_code=303)


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
    .admin-main { margin-left: 260px; padding: 32px 40px; min-height: 100vh; }
    .admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
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
    header_html = "".join(f"<th>{col.replace('_', ' ').title()}</th>" for col in columns)
    header_html += "<th>Actions</th>"

    rows_html = ""
    for record in records:
        cells = "".join(
            f"<td>{_truncate(str(getattr(record, col, '')))}</td>" for col in columns
        )
        rid = str(record.id)
        cells += f'<td><a href="/admin/{table_name}/{rid}" class="admin-btn admin-btn-ghost" style="padding:4px 12px;font-size:12px;">View</a></td>'
        rows_html += f"<tr>{cells}</tr>"

    pagination = ""
    if total_pages > 1:
        pages = ""
        for p in range(1, total_pages + 1):
            active = "admin-btn-primary" if p == page else "admin-btn-ghost"
            pages += f'<a href="/admin/{table_name}/?page={p}&q={search}" class="admin-btn {active}" style="padding:4px 12px;">{p}</a>'
        pagination = f'<div class="admin-pagination">{pages}</div>'

    return f"""<!DOCTYPE html>
<html lang="en"><head><title>{model_name} — Eden Admin</title>{_ADMIN_CSS}</head>
<body>
<div class="admin-sidebar">
    <h1>🌿 Eden Admin</h1>
    <a href="/admin/">Dashboard</a>
    <a href="/admin/{table_name}/" class="active">{model_name}</a>
</div>
<div class="admin-main">
    <div class="admin-header">
        <h2>{model_name} <span style="color:#64748B;font-size:16px;">({total})</span></h2>
        <div class="admin-search">
            <form method="get">
                <input type="text" name="q" placeholder="Search..." value="{search}">
            </form>
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
</body></html>"""


def _render_detail(model_name, table_name, record_id, fields, csrf_token="") -> str:
    fields_html = ""
    for key, value in fields:
        fields_html += f"""
        <div class="field-row">
            <div class="field-label">{key.replace('_', ' ')}</div>
            <div class="field-value">{_truncate(str(value), 500)}</div>
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


def _truncate(text: str, max_len: int = 80) -> str:
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text
