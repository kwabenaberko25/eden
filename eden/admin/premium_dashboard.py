"""
Eden Framework — Premium Unified Admin Dashboard (Pro Edition)

Self-contained HTML template with embedded CSS and JavaScript for a 
Single Page Application (SPA) admin experience.
"""

from datetime import datetime


class PremiumAdminTemplate:
    """Self-contained unified admin dashboard template with Pro features."""
    
    @staticmethod
    def render(api_base: str = "/admin/api", app_name: str = "Eden Framework") -> str:
        """
        Render complete unified admin dashboard HTML.
        
        Args:
            api_base: Base URL for API endpoints
            app_name: Application name for header
            
        Returns:
            Complete HTML string
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - {app_name}</title>
    <!-- Favicon -->
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🌿</text></svg>">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --secondary: #64748b;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --background: #f8fafc;
            --surface: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --sidebar-width: 260px;
            --header-height: 70px;
            --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--background);
            color: var(--text-main);
            overflow: hidden;
            display: flex;
            height: 100vh;
        }}

        /* SIDEBAR */
        .sidebar {{
            width: var(--sidebar-width);
            background: #1e1b4b; /* Dark indigo */
            color: white;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            z-index: 50;
        }}

        .sidebar-header {{
            height: var(--header-height);
            display: flex;
            align-items: center;
            padding: 0 24px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}

        .logo {{
            font-size: 20px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .sidebar-nav {{
            flex: 1;
            padding: 24px 12px;
            overflow-y: auto;
        }}

        .nav-section {{
            margin-bottom: 24px;
        }}

        .nav-label {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: rgba(255,255,255,0.4);
            padding: 0 12px;
            margin-bottom: 12px;
        }}

        .nav-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            border-radius: 8px;
            color: rgba(255,255,255,0.7);
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 4px;
        }}

        .nav-item:hover {{
            background: rgba(255,255,255,0.05);
            color: white;
        }}

        .nav-item.active {{
            background: var(--primary);
            color: white;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }}

        /* TOAST NOTIFICATIONS */
        .toast-container {{
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .toast {{
            background: #ffffff;
            border-radius: 8px;
            padding: 16px 20px;
            box-shadow: var(--shadow-lg);
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 300px;
            animation: slideInRight 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border-left: 4px solid var(--primary);
        }}

        @keyframes slideInRight {{
            from {{ transform: translateX(100%); opacity: 0; }}
            to {{ transform: translateX(0); opacity: 1; }}
        }}

        .toast.success {{ border-left-color: #10b981; }}
        .toast.error {{ border-left-color: #ef4444; }}

        /* DASHBOARD GRID */
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }}

        .stat-card {{
            background: var(--surface);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .stat-value {{
            font-size: 32px;
            font-weight: 700;
        }}

        /* MAIN CONTENT */
        .main-wrapper {{
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        .header {{
            height: var(--header-height);
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 32px;
        }}

        #content-area {{
            flex: 1;
            overflow-y: auto;
            padding: 32px;
        }}

        /* TABLES */
        .card {{
            background: var(--surface);
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            overflow: hidden;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            padding: 16px 24px;
            background: #f8fafc;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            border-bottom: 1px solid var(--border);
            text-align: left;
        }}

        td {{
            padding: 16px 24px;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}

        .btn {{
            padding: 8px 16px;
            border-radius: 6px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }}

        .btn-primary {{ background: var(--primary); color: white; }}
        .btn-secondary {{ background: #f1f5f9; color: var(--text-main); }}

        /* MODALS */
        .modal-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.5);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 20px;
        }}
        .modal-overlay.active {{ display: flex; }}
        .modal {{
            background: white;
            border-radius: 12px;
            width: 100%;
            max-width: 800px;
            max-height: 90vh;
            overflow-y: auto;
            padding: 32px;
        }}

        .form-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}

        .form-group {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .form-input {{
            padding: 10px 12px;
            border-radius: 6px;
            border: 1px solid var(--border);
            font-family: inherit;
        }}
    </style>
</head>
<body>
    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="logo">🌿 <span>Eden Elite</span></div>
        </div>
        <div class="sidebar-nav" id="sidebarNav"></div>
    </aside>

    <div class="main-wrapper">
        <header class="header">
            <div id="pageTitle" style="font-weight: 700; font-size: 20px;">Dashboard</div>
            <div id="userProfile" style="display: flex; align-items: center; gap: 12px; font-size: 14px; font-weight: 500; color: var(--text-muted);">
                <span id="userName">Loading...</span>
                <div style="width: 32px; height: 32px; border-radius: 50%; background: #e2e8f0; display: flex; align-items: center; justify-content: center; color: var(--text-main); font-weight: 700;" id="userAvatar">?</div>
                <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 12px;" onclick="doLogout()">Logout</button>
            </div>
        </header>

        <main id="content-area"></main>
    </div>

    <div id="toastContainer" class="toast-container"></div>

    <!-- Record Modal -->
    <div id="recordModal" class="modal-overlay">
        <div class="modal">
            <h3 id="modalTitle" style="margin-bottom: 24px;">Edit Record</h3>
            <form id="recordForm" class="form-grid"></form>
            <div id="inlinesContainer"></div>
            <div style="margin-top: 32px; display: flex; justify-content: flex-end; gap: 12px;">
                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="saveRecord()" id="saveBtn">Save Changes</button>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = "{api_base}";
        let registry = {{}};
        let currentTable = null;
        let currentRecordId = null;
        let records = [];
        let currentUser = null;

        // Simple client-side auth guard for SPA shell
        async function checkAuth() {{
            const urlParams = new URLSearchParams(window.location.search);
            const urlToken = urlParams.get('token');
            if (urlToken) {{
                console.log("Found token in URL, saving to localStorage");
                localStorage.setItem('admin_token', urlToken);
                // Clean the URL without reloading
                const newUrl = window.location.pathname + window.location.search.replace(/[?&]token=[^&]+/, '').replace(/^&/, '?');
                window.history.replaceState({{}}, document.title, newUrl || window.location.pathname);
            }}

            const token = localStorage.getItem('admin_token');
            return true;
        }}

        async function apiCall(endpoint, options = {{}}) {{
            const token = localStorage.getItem('admin_token');
            const headers = {{ 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }};
            
            if (token) {{
                headers['Authorization'] = `Bearer ${{token}}`;
            }}

            try {{
                const response = await fetch(API_BASE + endpoint, {{
                    headers: headers,
                    ...options,
                    credentials: 'include' 
                }});

                if (response.status === 401) {{
                    console.warn("API 401: Unauthorized. Clearing token and redirecting to login.");
                    localStorage.removeItem('admin_token');
                    // Force redirect to login
                    const basePath = window.location.pathname.replace(/\/login\/?$/, "").replace(/\/+$/, "");
                    window.location.href = basePath + "/login?next=" + encodeURIComponent(window.location.pathname);
                    return;
                }}

                if (response.status === 403) {{
                    const data = await response.json().catch(() => ({{ detail: "Access denied (Forbidden)." }}));
                    showError(data.detail || "You do not have permission to perform this action.");
                    throw new Error("Forbidden");
                }}

                if (!response.ok) {{
                    const data = await response.json().catch(() => ({{ detail: "Server Error" }}));
                    throw new Error(data.detail || `HTTP ${{response.status}}`);
                }}

                return await response.json();
            }} catch (err) {{
                if (err.message === "Forbidden") throw err;
                console.error(`API Call failed: ${{endpoint}}`, err);
                throw err;
            }}
        }}

        async function switchModel(table) {{
            currentTable = table;
            renderSidebar();
            
            if (table === null) {{
                document.getElementById('pageTitle').textContent = "Dashboard Overview";
                await loadDashboard();
                return;
            }}

            const model = registry[table];
            document.getElementById('pageTitle').textContent = model.label_plural;
            document.getElementById('content-area').innerHTML = '<p>Loading...</p>';
            await loadRecords();
        }}

        async function loadDashboard() {{
            const area = document.getElementById('content-area');
            area.innerHTML = '<p>Loading dashboard...</p>';
            try {{
                const data = await apiCall('/dashboard');
                let html = '<div class="dashboard-grid">';
                data.stats.forEach(s => {{
                    html += `
                        <div class="stat-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:14px; color:var(--text-muted); font-weight:600;">${{s.label}}</span>
                                <i class="${{s.icon}}" style="color:${{s.color}};"></i>
                            </div>
                            <div class="stat-value">${{s.value}}</div>
                            <div style="font-size:12px; font-weight:600;">${{s.trend}} vs last month</div>
                        </div>
                    `;
                }});
                html += '</div>';
                
                let modelsHtml = `
                    <div class="card" style="padding: 24px; margin-bottom: 24px;">
                        <h3 style="margin-bottom: 20px; font-size: 16px;">Quick Stats</h3>
                        <div style="display: grid; gap: 12px;">
                `;
                data.models.sort((a,b) => b.count - a.count).forEach(m => {{
                    const itemHtml = `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-radius: 8px; background: #f8fafc; border: 1px solid var(--border);">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <i class="${{m.icon}}" style="color: var(--primary);"></i>
                                <span style="font-weight: 600; font-size: 14px;">${{m.label}}</span>
                            </div>
                            <span style="font-weight: 700; color: var(--text-muted);">${{m.count}}</span>
                        </div>
                    `;
                    modelsHtml += itemHtml;
                }});
                modelsHtml += '</div></div>';
                html += modelsHtml;

                html += '<div class="card" style="padding: 24px;"><h3>Recent Activity</h3>';
                data.activities.forEach(a => {{
                    html += `<div style="padding:12px 0; border-bottom:1px solid var(--border);">
                        <strong>${{a.action}}</strong> on ${{a.model}} by ${{a.user}} • ${{a.time_human}}
                    </div>`;
                }});
                html += '</div>';
                
                area.innerHTML = html;
            }} catch (err) {{
                showError("Failed to load dashboard.");
            }}
        }}

        async function loadRecords() {{
            try {{
                const data = await apiCall(`/${{currentTable}}/list`);
                records = data.items || data;
                renderTable();
            }} catch (err) {{
                showError("Failed to load records.");
            }}
        }}

        function renderTable() {{
            const model = registry[currentTable];
            let html = '<div class="card"><table><thead><tr>';
            model.list_display.forEach(col => html += `<th>${{col.replace(/_/g, ' ')}}</th>`);
            html += '<th style="text-align:right;">Actions</th></tr></thead><tbody>';
            
            records.forEach(r => {{
                html += `<tr>`;
                model.list_display.forEach(col => html += `<td>${{r[col]}}</td>`);
                html += `<td style="text-align:right;">
                    <button class="btn btn-secondary" style="padding: 4px 8px;" onclick="editRecord('${{r.id}}')">Edit</button>
                    <button class="btn" style="padding: 4px 8px; color:var(--danger);" onclick="deleteRecord('${{r.id}}')"><i class="fa-solid fa-trash"></i></button>
                </td></tr>`;
            }});
            
            html += '</tbody></table></div>';
            document.getElementById('content-area').innerHTML = html;
        }}

        async function deleteRecord(id) {{
            if (!confirm("Are you sure?")) return;
            try {{
                await apiCall(`/${{currentTable}}/delete/${{id}}`, {{ method: 'DELETE' }});
                showSuccess("Deleted successfully");
                loadRecords();
            }} catch (err) {{
                showError(err.message);
            }}
        }}

        async function editRecord(id) {{
            currentRecordId = id;
            document.getElementById('modalTitle').textContent = "Edit Record";
            const record = records.find(r => String(r.id) === String(id));
            renderForm(record);
            document.getElementById('recordModal').classList.add('active');
        }}

        function renderForm(record = null) {{
            const form = document.getElementById('recordForm');
            const model = registry[currentTable];
            let html = '';
            
            model.fields.forEach(f => {{
                const val = record ? record[f.key] : '';
                html += `
                    <div class="form-group">
                        <label style="font-size:13px; font-weight:600;">${{f.label}}</label>
                        <input type="text" name="${{f.key}}" class="form-input" value="${{val}}">
                    </div>
                `;
            }});
            form.innerHTML = html;
        }}

        async function saveRecord() {{
            const form = document.getElementById('recordForm');
            const formData = new FormData(form);
            const body = {{}};
            formData.forEach((v, k) => body[k] = v);
            
            try {{
                await apiCall(`/${{currentTable}}/update/${{currentRecordId}}`, {{
                    method: 'PATCH',
                    body: JSON.stringify(body)
                }});
                showSuccess("Successfully saved!");
                closeModal();
                loadRecords();
            }} catch (err) {{
                showError(err.message);
            }}
        }}

        function closeModal() {{ document.getElementById('recordModal').classList.remove('active'); }}

        function renderSidebar() {{
            const nav = document.getElementById('sidebarNav');
            let html = `
                <div class="nav-section">
                    <div class="nav-item ${{currentTable === null ? 'active' : ''}}" onclick="switchModel(null)">
                        <i class="fa-solid fa-chart-line"></i> <span>Dashboard Overview</span>
                    </div>
                </div>
                <div class="nav-section">
                    <div class="nav-label">Models</div>
            `;
            Object.values(registry).forEach(m => {{
                html += `
                    <div class="nav-item ${{currentTable === m.table ? 'active' : ''}}" onclick="switchModel('${{m.table}}')">
                        <i class="${{m.icon}}"></i> <span>${{m.label_plural}}</span>
                    </div>
                `;
            }});
            nav.innerHTML = html;
        }}

        function showToast(msg, type) {{
            const container = document.getElementById('toastContainer');
            const t = document.createElement('div');
            t.className = `toast ${{type}}`;
            t.innerHTML = `<i class="fa-solid fa-info-circle"></i> <span>${{msg}}</span>`;
            container.appendChild(t);
            setTimeout(() => {{
                t.style.opacity = '0';
                t.style.transform = 'translateX(20px)';
                setTimeout(() => t.remove(), 300);
            }}, 4000);
        }}

        function showSuccess(msg) {{ showToast(msg, 'success'); }}
        function showError(msg) {{ showToast(msg, 'error'); }}

        async function loadProfile() {{
            try {{
                const user = await apiCall('/me');
                document.getElementById('userName').textContent = user.username;
                document.getElementById('userAvatar').textContent = user.username[0].toUpperCase();
            }} catch (err) {{
                console.error("Failed to load profile", err);
            }}
        }}

        async function doLogout() {{
            if (!confirm("Are you sure you want to log out?")) return;
            try {{
                await apiCall('/logout', {{ method: 'POST' }});
            }} catch (err) {{
                console.error("Logout error", err);
            }} finally {{
                localStorage.removeItem('admin_token');
                checkAuth();
            }}
        }}

        document.addEventListener('DOMContentLoaded', async () => {{
            if (!await checkAuth()) return;
            
            try {{
                // Load metadata and profile in parallel
                const [meta] = await Promise.all([
                    apiCall('/metadata'),
                    loadProfile()
                ]);
                registry = meta;
                switchModel(null);
            }} catch (err) {{
                console.error("Initialization failed", err);
                showError("Connection lost. Please sign in again.");
                setTimeout(() => checkAuth(), 2000);
            }}
        }});
    </script>
</body>
</html>"""
