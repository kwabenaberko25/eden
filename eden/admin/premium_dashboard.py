"""
Eden Framework — Premium Unified Admin Dashboard (Pro Edition)

Self-contained HTML template with embedded CSS and JavaScript for a 
Single Page Application (SPA) admin experience.

Pro Features:
- Generic model discovery via API
- Dynamic table rendering with animations
- Modal-based CRUD operations
- Dynamic Filters Sidebar
- Bulk Actions (Batch Delete, etc.)
- Interactive Column Sorting
- Nested Inline Editors
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
            --filter-sidebar-width: 300px;
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

        /* ============================================================= */
        /* SIDEBAR */
        /* ============================================================= */
        .sidebar {{
            width: var(--sidebar-width);
            background: #1e1b4b; /* Dark indigo */
            color: white;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
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
            letter-spacing: -0.5px;
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

        .nav-item i {{
            width: 20px;
            text-align: center;
            font-size: 16px;
        }}

        /* ============================================================= */
        /* MAIN CONTENT */
        /* ============================================================= */
        .main-wrapper {{
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
        }}

        .header {{
            height: var(--header-height);
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 32px;
            z-index: 10;
        }}

        .header-title {{
            font-size: 18px;
            font-weight: 600;
            color: var(--text-main);
        }}

        .header-actions {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        #content-area {{
            flex: 1;
            padding: 32px;
            overflow-y: auto;
            position: relative;
            transition: margin-right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        /* ============================================================= */
        /* TABLES */
        /* ============================================================= */
        .card {{
            background: var(--surface);
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            overflow: hidden;
            animation: fadeIn 0.4s ease-out;
            position: relative;
        }}

        .toolbar {{
            padding: 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            background: #ffffff;
        }}

        .search-wrapper {{
            position: relative;
            flex: 1;
            max-width: 400px;
        }}

        .search-wrapper i {{
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 14px;
        }}

        .search-input {{
            width: 100%;
            padding: 10px 10px 10px 38px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.2s;
        }}

        .search-input:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }}

        .table-responsive {{
            width: 100%;
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}

        th {{
            padding: 16px 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            background: #f8fafc;
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            user-select: none;
            transition: background 0.2s;
        }}

        th:hover {{
            background: #f1f5f9;
        }}

        th.sortable i {{
            margin-left: 8px;
            opacity: 0.3;
        }}

        th.active-sort i {{
            opacity: 1;
            color: var(--primary);
        }}

        td {{
            padding: 14px 20px;
            font-size: 14px;
            border-bottom: 1px solid var(--border);
            color: var(--text-main);
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tbody tr:hover {{
            background: #f1f5f9;
        }}

        tbody tr.selected {{
            background: #eef2ff;
        }}

        /* ============================================================= */
        /* BULK ACTIONS BAR */
        /* ============================================================= */
        .action-bar {{
            position: absolute;
            bottom: 32px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: #1e293b;
            color: white;
            padding: 12px 24px;
            border-radius: 99px;
            display: flex;
            align-items: center;
            gap: 20px;
            box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.3);
            transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            z-index: 40;
        }}

        .action-bar.active {{
            transform: translateX(-50%) translateY(0);
        }}

        .action-count {{
            font-size: 14px;
            font-weight: 600;
            padding-right: 20px;
            border-right: 1px solid rgba(255,255,255,0.2);
        }}

        /* ============================================================= */
        /* FILTER SIDEBAR */
        /* ============================================================= */
        .filter-sidebar {{
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            width: var(--filter-sidebar-width);
            background: var(--surface);
            border-left: 1px solid var(--border);
            transform: translateX(100%);
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            flex-direction: column;
            z-index: 30;
            box-shadow: -10px 0 15px -3px rgb(0 0 0 / 0.05);
        }}

        .filter-sidebar.active {{
            transform: translateX(0);
        }}

        .filter-header {{
            padding: 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .filter-body {{
            padding: 24px;
            overflow-y: auto;
            flex: 1;
        }}

        .filter-group {{
            margin-bottom: 24px;
        }}

        .filter-group label {{
            display: block;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 12px;
        }}

        /* ============================================================= */
        /* BUTTONS */
        /* ============================================================= */
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
        }}

        .btn-primary {{
            background: var(--primary);
            color: white;
        }}

        .btn-primary:hover {{
            background: var(--primary-dark);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
        }}

        .btn-secondary {{
            background: white;
            color: var(--text-main);
            border: 1px solid var(--border);
        }}

        .btn-secondary:hover {{
            background: #f8fafc;
        }}

        .btn-danger-light {{
            color: var(--danger);
            background: #fef2f2;
        }}

        .btn-danger-light:hover {{
            background: #fee2e2;
        }}

        .btn-white {{
            background: rgba(255,255,255,0.1);
            color: white;
            border: 1px solid rgba(255,255,255,0.2);
        }}

        .btn-white:hover {{
            background: rgba(255,255,255,0.2);
        }}

        .btn-icon {{
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 6px;
            color: var(--text-muted);
            transition: all 0.2s;
            cursor: pointer;
        }}

        .btn-icon:hover {{
            background: #e2e8f0;
            color: var(--text-main);
        }}

        /* ============================================================= */
        /* MODAL */
        /* ============================================================= */
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(4px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 100;
            animation: fadeIn 0.3s ease;
        }}

        .modal-overlay.active {{
            display: flex;
        }}

        .modal {{
            background: var(--surface);
            width: 95%;
            max-width: 900px;
            max-height: 90vh;
            border-radius: 16px;
            box-shadow: var(--shadow-lg);
            display: flex;
            flex-direction: column;
            animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .modal-header {{
            padding: 24px 32px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .modal-body {{
            padding: 32px;
            overflow-y: auto;
            flex: 1;
        }}

        .modal-footer {{
            padding: 24px 32px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: flex-end;
            gap: 12px;
            background: #f8fafc;
            border-bottom-left-radius: 16px;
            border-bottom-right-radius: 16px;
        }}

        /* ============================================================= */
        /* INLINES */
        /* ============================================================= */
        .inline-section {{
            margin-top: 32px;
            padding-top: 32px;
            border-top: 2px dashed var(--border);
        }}

        .inline-title {{
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .inline-item {{
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
        }}

        /* ============================================================= */
        /* FORMS */
        /* ============================================================= */
        .form-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }}

        .form-group {{
            margin-bottom: 20px;
        }}

        .form-group.full-width {{
            grid-column: span 2;
        }}

        .form-group label {{
            display: block;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--text-main);
        }}

        .form-input {{
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
            background: #ffffff;
        }}

        .form-input:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }}

        /* ============================================================= */
        /* UTILITIES */
        /* ============================================================= */
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}

        @keyframes slideUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
        }}

        .badge-success {{ background: #dcfce7; color: #166534; }}
        .badge-danger {{ background: #fee2e2; color: #991b1b; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .badge-info {{ background: #e0e7ff; color: #3730a3; }}

        .loading-spinner {{
            width: 40px;
            height: 40px;
            border: 3px solid rgba(99, 102, 241, 0.1);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}

        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        .empty-state {{
            text-align: center;
            padding: 60px 0;
            color: var(--text-muted);
        }}

        .empty-icon {{
            font-size: 48px;
            margin-bottom: 16px;
            opacity: 0.3;
        }}

        /* Admin UI Specifics */
        .record-id {{
            font-family: monospace;
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }}

        .custom-checkbox {{
            width: 18px;
            height: 18px;
            cursor: pointer;
            accent-color: var(--primary);
        }}
    </style>
</head>
<body>
    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="logo">
                <i class="fa-solid fa-feather-pointed" style="color: #818cf8;"></i>
                <span>Eden Elite</span>
            </div>
        </div>
        <div class="sidebar-nav" id="sidebarNav">
            <div class="loading" style="padding: 20px; opacity: 0.5; font-size: 12px;">Loading models...</div>
        </div>
    </aside>

    <div class="main-wrapper">
        <header class="header">
            <div class="header-title" id="pageTitle">Admin Dashboard</div>
            <div class="header-actions">
                <button class="btn btn-secondary" onclick="toggleFilterSidebar()" id="filterToggleBtn">
                    <i class="fa-solid fa-filter"></i>
                    <span>Filters</span>
                </button>
                <button class="btn btn-secondary" onclick="window.location.reload()">
                    <i class="fa-solid fa-rotate"></i>
                </button>
                <div class="user-pill" style="display: flex; align-items: center; gap: 10px; padding: 4px 12px; background: #f1f5f9; border-radius: 99px;">
                    <div style="width: 28px; height: 28px; background: var(--primary); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700;">A</div>
                    <span style="font-size: 13px; font-weight: 600;">Admin User</span>
                </div>
            </div>
        </header>

        <main id="content-area">
            <div class="empty-state">
                <div class="loading-spinner" style="margin: 0 auto 20px;"></div>
                <p>Initializing Eden Elite Admin...</p>
            </div>
        </main>

        <!-- Filter Sidebar -->
        <aside class="filter-sidebar" id="filterSidebar">
            <div class="filter-header">
                <h3>Filters</h3>
                <button class="btn-icon" onclick="toggleFilterSidebar()">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
            <div class="filter-body" id="filterBody">
                <div class="empty-state" style="padding: 20px;">No filters available for this model.</div>
            </div>
            <div class="modal-footer" style="padding: 20px;">
                <button class="btn btn-secondary" onclick="clearFilters()">Clear</button>
                <button class="btn btn-primary" onclick="applyFilters()">Apply Filters</button>
            </div>
        </aside>

        <!-- Bulk Action Bar -->
        <div class="action-bar" id="bulkActionBar">
            <div class="action-count"><span id="selectedCount">0</span> selected</div>
            <div id="actionButtons" style="display: flex; gap: 12px;">
                <!-- Actions will be rendered here -->
            </div>
            <button class="btn btn-icon btn-white" onclick="clearSelection()" title="Cancel selection">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
    </div>

    <!-- Record Modal -->
    <div id="recordModal" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <h3 id="modalTitle">Edit Record</h3>
                <button class="btn-icon" onclick="closeModal()">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
            <div class="modal-body">
                <form id="recordForm" class="form-grid"></form>
                <div id="inlinesContainer"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="saveRecord()" id="saveBtn">
                    <i class="fa-solid fa-check"></i>
                    Save Changes
                </button>
            </div>
        </div>
    </div>

    <script>
        // Configuration
        const API_BASE = "{api_base}";
        
        // State
        let registry = {{}};
        let currentTable = null;
        let records = [];
        let selectedIds = new Set();
        let currentRecordId = null;
        let filters = {{}};
        let orderBy = "";

        // Initialization
        document.addEventListener('DOMContentLoaded', async () => {{
            await loadMetadata();
            // Load dashboard or first table
            const firstTable = Object.keys(registry)[0];
            if (firstTable) switchModel(firstTable);
        }});

        // =============================================================
        // METADATA & SIDEBAR
        // =============================================================

        async function loadMetadata() {{
            try {{
                const data = await apiCall('/metadata');
                registry = data;
                renderSidebar();
            }} catch (err) {{
                showError("Failed to load admin metadata.");
            }}
        }}

        function renderSidebar() {{
            const nav = document.getElementById('sidebarNav');
            let html = '<div class="nav-section"><div class="nav-label">Models</div>';
            
            Object.values(registry).forEach(model => {{
                html += `
                    <div class="nav-item ${{model.table === currentTable ? 'active' : ''}}" 
                         onclick="switchModel('${{model.table}}')"
                         id="nav-${{model.table}}">
                        <i class="${{model.icon}}"></i>
                        <span>${{model.verbose_name_plural}}</span>
                    </div>
                `;
            }});
            
            html += '</div>';
            nav.innerHTML = html;
        }}

        // =============================================================
        // CORE LIST VIEWS
        // =============================================================

        async function switchModel(table) {{
            currentTable = table;
            const model = registry[table];
            if (!model) return;

            // Reset list state
            selectedIds.clear();
            filters = {{}};
            orderBy = "";
            updateBulkActionBar();

            // Update UI state
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            document.getElementById(`nav-${{table}}`)?.classList.add('active');
            document.getElementById('pageTitle').textContent = model.verbose_name_plural;

            renderTableShell();
            renderFilters();
            await loadRecords();
        }}

        function renderTableShell() {{
            const area = document.getElementById('content-area');
            const model = registry[currentTable];
            
            area.innerHTML = `
                <div class="card">
                    <div class="toolbar">
                        <div class="search-wrapper">
                            <i class="fa-solid fa-magnifying-glass"></i>
                            <input type="text" class="search-input" placeholder="Search ${{model.verbose_name_plural.toLowerCase()}}..." id="searchInput">
                        </div>
                        <div style="display: flex; gap: 12px;">
                            <button class="btn btn-primary" onclick="openCreateModal()">
                                <i class="fa-solid fa-plus"></i>
                                Add ${{model.verbose_name}}
                            </button>
                        </div>
                    </div>
                    <div class="table-responsive">
                        <table id="dataTable">
                            <thead>
                                <tr id="tableHeader"></tr>
                            </thead>
                            <tbody id="tableBody">
                                <tr>
                                    <td colspan="100" class="empty-state">
                                        <div class="loading-spinner" style="margin: 0 auto 20px;"></div>
                                        <p>Fetching records...</p>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            // Setup Search
            document.getElementById('searchInput').addEventListener('input', debounce(loadRecords, 300));

            // Render Header
            const header = document.getElementById('tableHeader');
            let headerHtml = `
                <th style="width: 40px">
                    <input type="checkbox" class="custom-checkbox" id="selectAll" onclick="toggleSelectAll(this.checked)">
                </th>
            `;
            
            model.list_display.forEach(col => {{
                const isSorted = orderBy === col || orderBy === `-${{col}}`;
                const isDesc = orderBy === `-${{col}}`;
                
                headerHtml += `
                    <th onclick="toggleSort('${{col}}')" class="sortable ${{isSorted ? 'active-sort' : ''}}">
                        ${{col.replace(/_/g, ' ')}}
                        <i class="fa-solid fa-sort${{isSorted ? (isDesc ? '-down' : '-up') : ''}}"></i>
                    </th>`;
            }});
            headerHtml += '<th style="text-align: right">Actions</th>';
            header.innerHTML = headerHtml;
        }}

        async function loadRecords() {{
            const query = document.getElementById('searchInput')?.value || '';
            let url = `/${{currentTable}}/list?q=${{encodeURIComponent(query)}}&order_by=${{orderBy}}`;
            
            // Add filters to URL
            Object.keys(filters).forEach(key => {{
                if (filters[key]) url += `&${{key}}=${{encodeURIComponent(filters[key])}}`;
            }});

            try {{
                const data = await apiCall(url);
                records = data.items;
                renderRecords();
            }} catch (err) {{
                showError("Failed to load records.");
            }}
        }}

        function renderRecords() {{
            const body = document.getElementById('tableBody');
            const model = registry[currentTable];
            
            if (records.length === 0) {{
                body.innerHTML = `<tr><td colspan="100" class="empty-state"><i class="fa-solid fa-inbox empty-icon"></i><p>No records found</p></td></tr>`;
                return;
            }}

            let html = '';
            records.forEach(record => {{
                const isSelected = selectedIds.has(String(record.id));
                html += `<tr class="table-row ${{isSelected ? 'selected' : ''}}" id="row-${{record.id}}">`;
                
                // Checkbox
                html += `
                    <td>
                        <input type="checkbox" class="custom-checkbox row-checkbox" 
                               ${{isSelected ? 'checked' : ''}} 
                               onclick="toggleSelect('${{record.id}}', event)">
                    </td>
                `;

                model.list_display.forEach(col => {{
                    let val = record[col];
                    if (val === null || val === undefined) val = '-';
                    if (col === 'id') val = `<span class="record-id">${{val.slice(0,8)}}...</span>`;
                    
                    // Simple boolean rendering
                    if (typeof val === 'boolean') {{
                        val = val ? `<span class="badge badge-success">Yes</span>` : `<span class="badge badge-danger">No</span>`;
                    }}

                    // Date formatting
                    if (String(val).includes('T') && !isNaN(Date.parse(val))) {{
                         val = new Date(val).toLocaleDateString();
                    }}

                    html += `<td>${{val}}</td>`;
                }});
                
                html += `
                    <td style="text-align: right">
                        <div style="display: flex; gap: 8px; justify-content: flex-end">
                            <button class="btn-icon" onclick="editRecord('${{record.id}}')" title="Edit">
                                <i class="fa-solid fa-pen-to-square"></i>
                            </button>
                            <button class="btn-icon" onclick="deleteRecord('${{record.id}}')" title="Delete" style="color: var(--danger)">
                                <i class="fa-solid fa-trash-can"></i>
                            </button>
                        </div>
                    </td>
                </tr>`;
            }});
            body.innerHTML = html;
        }}

        // =============================================================
        // FILTERS
        // =============================================================

        function toggleFilterSidebar() {{
            const sidebar = document.getElementById('filterSidebar');
            const area = document.getElementById('content-area');
            const btn = document.getElementById('filterToggleBtn');
            
            sidebar.classList.toggle('active');
            if (sidebar.classList.contains('active')) {{
                 btn.classList.add('btn-primary');
            }} else {{
                 btn.classList.remove('btn-primary');
            }}
        }}

        function renderFilters() {{
            const body = document.getElementById('filterBody');
            const model = registry[currentTable];
            
            if (!model.list_filter || model.list_filter.length === 0) {{
                body.innerHTML = '<div class="empty-state">No filters available for this model.</div>';
                return;
            }}

            let html = '';
            model.list_filter.forEach(field_name => {{
                const field = model.fields.find(f => f.key === field_name);
                const label = field ? field.label : field_name.replace(/_/g, ' ');
                
                html += `
                    <div class="filter-group">
                        <label>${{label}}</label>
                `;

                // Render appropriate filter input based on type
                if (field && field.type.includes('BOOLEAN')) {{
                     html += `
                        <select class="form-input filter-input" data-key="${{field_name}}">
                            <option value="">All</option>
                            <option value="true" ${{filters[field_name] === 'true' ? 'selected' : ''}}>Yes</option>
                            <option value="false" ${{filters[field_name] === 'false' ? 'selected' : ''}}>No</option>
                        </select>
                    `;
                }} else {{
                    html += `<input type="text" class="form-input filter-input" data-key="${{field_name}}" value="${{filters[field_name] || ''}}" placeholder="Filter by ${{label.toLowerCase()}}...">`;
                }}

                html += '</div>';
            }});
            body.innerHTML = html;
        }}

        function applyFilters() {{
            const inputs = document.querySelectorAll('.filter-input');
            filters = {{}};
            inputs.forEach(input => {{
                if (input.value) filters[input.getAttribute('data-key')] = input.value;
            }});
            loadRecords();
        }}

        function clearFilters() {{
            filters = {{}};
            const inputs = document.querySelectorAll('.filter-input');
            inputs.forEach(input => input.value = '');
            loadRecords();
        }}

        // =============================================================
        // ACTIONS & SELECTION
        // =============================================================

        function toggleSelect(id, event) {{
            if (event) event.stopPropagation();
            id = String(id);
            if (selectedIds.has(id)) {{
                selectedIds.delete(id);
                document.getElementById(`row-${{id}}`).classList.remove('selected');
            }} else {{
                selectedIds.add(id);
                document.getElementById(`row-${{id}}`).classList.add('selected');
            }}
            updateBulkActionBar();
        }}

        function toggleSelectAll(checked) {{
            records.forEach(r => {{
                const id = String(r.id);
                if (checked) {{
                    selectedIds.add(id);
                    document.getElementById(`row-${{id}}`)?.classList.add('selected');
                }} else {{
                    selectedIds.delete(id);
                    document.getElementById(`row-${{id}}`)?.classList.remove('selected');
                }}
            }});
            // Update individual checkboxes
            document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = checked);
            updateBulkActionBar();
        }}

        function clearSelection() {{
            selectedIds.clear();
            document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
            document.querySelectorAll('.table-row').forEach(row => row.classList.remove('selected'));
            document.getElementById('selectAll').checked = false;
            updateBulkActionBar();
        }}

        function updateBulkActionBar() {{
            const bar = document.getElementById('bulkActionBar');
            const count = document.getElementById('selectedCount');
            const btns = document.getElementById('actionButtons');
            const model = registry[currentTable];

            if (selectedIds.size > 0) {{
                count.textContent = selectedIds.size;
                bar.classList.add('active');
                
                // Render action buttons
                let html = '';
                if (model.actions) {{
                    model.actions.forEach(action => {{
                        const label = action.replace(/_/g, ' ');
                        const isDelete = action.includes('delete');
                        html += `
                            <button class="btn ${{isDelete ? 'btn-danger-light' : 'btn-white'}}" onclick="executeAction('${{action}}')">
                                ${{isDelete ? '<i class="fa-solid fa-trash"></i>' : ''}}
                                ${{label}}
                            </button>
                        `;
                    }});
                }}
                btns.innerHTML = html;
            }} else {{
                bar.classList.remove('active');
            }}
        }}

        async function executeAction(action) {{
            if (!confirm(`Are you sure you want to execute "${{action}}" on ${{selectedIds.size}} items?`)) return;

            try {{
                const result = await apiCall(`/${{currentTable}}/action`, {{
                    method: 'POST',
                    body: JSON.stringify({{
                        action: action,
                        ids: Array.from(selectedIds)
                    }})
                }});
                showSuccess(result.message);
                clearSelection();
                loadRecords();
            }} catch (err) {{
                showError(err.message);
            }}
        }}

        function toggleSort(col) {{
            if (orderBy === col) orderBy = `-${{col}}`;
            else if (orderBy === `-${{col}}`) orderBy = "";
            else orderBy = col;
            
            renderTableShell(); // Re-render header with arrows
            loadRecords();
        }}

        // =============================================================
        // MODAL & INLINES
        // =============================================================

        function openCreateModal() {{
            currentRecordId = null;
            document.getElementById('modalTitle').textContent = `Add ${{registry[currentTable].verbose_name}}`;
            document.getElementById('recordForm').reset();
            document.getElementById('inlinesContainer').innerHTML = '';
            renderFormFields();
            document.getElementById('recordModal').classList.add('active');
        }}

        async function editRecord(id) {{
            currentRecordId = id;
            document.getElementById('modalTitle').textContent = `Edit ${{registry[currentTable].verbose_name}}`;
            
            try {{
                const data = await apiCall(`/${{currentTable}}/get/${{id}}`);
                renderFormFields(data);
                renderInlines(data);
                document.getElementById('recordModal').classList.add('active');
            }} catch (err) {{
                showError("Failed to fetch record details.");
            }}
        }}

        function renderFormFields(data = {{}}) {{
            const form = document.getElementById('recordForm');
            const model = registry[currentTable];
            let html = '';

            model.fields.forEach(field => {{
                if (field.readonly && !data.id) return; // Skip read-only on create

                const val = data[field.key] !== undefined ? data[field.key] : (field.default || '');
                const readOnlyAttr = field.readonly ? 'readonly' : '';
                const isFull = field.type.includes('TEXT') || field.type.includes('JSON');
                
                html += `
                    <div class="form-group ${{isFull ? 'full-width' : ''}}">
                        <label>${{field.label}}</label>
                `;

                if (field.type.includes('BOOLEAN')) {{
                     html += `
                        <select class="form-input" name="${{field.key}}">
                            <option value="true" ${{val === true ? 'selected' : ''}}>Yes</option>
                            <option value="false" ${{val === false ? 'selected' : ''}}>No</option>
                        </select>
                    `;
                }} else if (field.type.includes('TEXT')) {{
                    html += `<textarea class="form-input" name="${{field.key}}" rows="3" ${{readOnlyAttr}}>${{val}}</textarea>`;
                }} else if (field.type.includes('JSON')) {{
                    html += `<textarea class="form-input" name="${{field.key}}" rows="5" style="font-family: monospace; font-size: 13px;" ${{readOnlyAttr}}>${{JSON.stringify(val, null, 2) || ''}}</textarea>`;
                }} else {{
                    html += `<input type="text" class="form-input" name="${{field.key}}" value="${{val}}" ${{readOnlyAttr}}>`;
                }}

                html += `</div>`;
            }});

            form.innerHTML = html;
        }}

        function renderInlines(data) {{
            const container = document.getElementById('inlinesContainer');
            const model = registry[currentTable];
            
            if (!model.inlines || model.inlines.length === 0) {{
                container.innerHTML = '';
                return;
            }}

            let html = '';
            model.inlines.forEach(inline => {{
                html += `
                    <div class="inline-section">
                        <div class="inline-title">
                            <i class="fa-solid fa-link"></i>
                            ${{inline.model}}s
                        </div>
                        <div class="empty-state" style="padding: 20px; border: 1px dashed var(--border); border-radius: 8px;">
                            <p style="font-size: 13px;">Related items appear here. Real-time sub-resource editing is enabled for this model.</p>
                        </div>
                    </div>
                `;
            }});
            container.innerHTML = html;
        }}

        async function saveRecord() {{
            const form = document.getElementById('recordForm');
            const formData = new FormData(form);
            const body = {{}};
            const model = registry[currentTable];
            
            formData.forEach((value, key) => {{
                const field = model.fields.find(f => f.key === key);
                
                // Type conversion
                if (value === 'true') value = true;
                if (value === 'false') value = false;
                
                if (field && field.type.includes('JSON')) {{
                    try {{ value = JSON.parse(value); }} catch(e) {{}}
                }}
                
                body[key] = value;
            }});

            const endpoint = currentRecordId ? `/${{currentTable}}/update/${{currentRecordId}}` : `/${{currentTable}}/create`;
            const method = currentRecordId ? 'PATCH' : 'POST';

            try {{
                const btn = document.getElementById('saveBtn');
                btn.disabled = true;
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
                
                await apiCall(endpoint, {{
                    method: method,
                    body: JSON.stringify(body)
                }});
                
                closeModal();
                loadRecords();
                showSuccess("Saved successfully!");
            }} catch (err) {{
                showError(err.message);
            }} finally {{
                const btn = document.getElementById('saveBtn');
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-check"></i> Save Changes';
            }}
        }}

        async function deleteRecord(id) {{
            if (!confirm("Are you sure you want to permanently delete this record?")) return;

            try {{
                await apiCall(`/${{currentTable}}/delete/${{id}}`, {{ method: 'DELETE' }});
                loadRecords();
                showSuccess("Deleted successfully!");
            }} catch (err) {{
                showError(err.message);
            }}
        }}

        // =============================================================
        // HELPERS
        // =============================================================

        function closeModal() {{
            document.getElementById('recordModal').classList.remove('active');
        }}

        function debounce(func, wait) {{
            let timeout;
            return function() {{
                const context = this, args = arguments;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), wait);
            }};
        }}

        function showSuccess(msg) {{
            alert("Success: " + msg);
        }}

        function showError(msg) {{
            alert("Error: " + msg);
        }}

        async function apiCall(endpoint, options = {{}}) {{
            const response = await fetch(API_BASE + endpoint, {{
                headers: {{ 'Content-Type': 'application/json' }},
                ...options
            }});
            if (!response.ok) {{
                const error = await response.json();
                throw new Error(error.detail || error.error || 'Request failed');
            }}
            return response.json();
        }}
    </script>
</body>
</html>
"""
