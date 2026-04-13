"""
Eden Framework Admin Panel — HTML Template (DEPRECATED)

DEPRECATED: This module provides a legacy dashboard for feature flags only.

The new unified admin dashboard is available via:
    from eden.admin.premium_dashboard import PremiumAdminTemplate
    
The new dashboard includes:
- All model management (not just flags)
- Feature flags as a virtual model in the sidebar
- Complete CRUD operations
- Search, filtering, and sorting

This template is kept for backward compatibility with existing code.
New projects should use the PremiumAdminTemplate instead.

Generates self-contained HTML with embedded CSS and JavaScript.
No external dependencies, no internet required.

Legacy Usage:
    from eden.admin.dashboard_template import AdminDashboardTemplate
    
    html = AdminDashboardTemplate.render(
        api_base="/admin/flags",
        app_name="Eden Framework"
    )
    
    # Save to file or serve via FastAPI
    return HTMLResponse(html)
"""

from datetime import datetime
import warnings


class AdminDashboardTemplate:
    """Self-contained admin dashboard template (DEPRECATED - use PremiumAdminTemplate instead)."""
    
    @staticmethod
    def render(api_base: str = "/admin/flags", app_name: str = "Eden Framework") -> str:
        """
        Render complete admin dashboard HTML.
        
        DEPRECATED: Use PremiumAdminTemplate instead for the new unified dashboard.
        
        Args:
            api_base: Base URL for API endpoints
            app_name: Application name for header
            
        Returns:
            Complete HTML string (offline-capable)
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feature Flags Admin - {app_name}</title>
    <style>
        /* ============================================================= */
        /* RESET & BASE STYLES */
        /* ============================================================= */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html, body {{
            height: 100%;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f7fa;
            color: #333;
        }}
        
        /* ============================================================= */
        /* LAYOUT */
        /* ============================================================= */
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        header h1 {{
            font-size: 28px;
            font-weight: 600;
        }}
        
        header p {{
            font-size: 14px;
            opacity: 0.9;
            margin-top: 5px;
        }}
        
        /* ============================================================= */
        /* NAVIGATION & CONTROLS */
        /* ============================================================= */
        .controls {{
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .search-box {{
            flex: 1;
            min-width: 250px;
        }}
        
        .search-box input {{
            width: 100%;
            padding: 10px 15px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }}
        
        .search-box input:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        
        .button-group {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        
        button {{
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .btn-primary {{
            background: #667eea;
            color: white;
        }}
        
        .btn-primary:hover {{
            background: #5568d3;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        
        .btn-secondary {{
            background: #e0e7ff;
            color: #667eea;
        }}
        
        .btn-secondary:hover {{
            background: #c7d2fd;
        }}
        
        .btn-danger {{
            background: #ef4444;
            color: white;
        }}
        
        .btn-danger:hover {{
            background: #dc2626;
        }}
        
        .btn-success {{
            background: #10b981;
            color: white;
        }}
        
        .btn-success:hover {{
            background: #059669;
        }}
        
        /* ============================================================= */
        /* STATS CARDS */
        /* ============================================================= */
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        
        .stat-card h3 {{
            font-size: 12px;
            font-weight: 600;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }}
        
        .stat-card .value {{
            font-size: 32px;
            font-weight: 700;
            color: #333;
        }}
        
        .stat-card .subtitle {{
            font-size: 12px;
            color: #999;
            margin-top: 10px;
        }}
        
        /* ============================================================= */
        /* FLAGS TABLE */
        /* ============================================================= */
        .table-container {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        thead {{
            background: #f9fafb;
            border-bottom: 2px solid #e5e7eb;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 15px;
            border-bottom: 1px solid #f3f4f6;
        }}
        
        tbody tr:hover {{
            background: #f9fafb;
        }}
        
        /* ============================================================= */
        /* FLAG BADGE */
        /* ============================================================= */
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .badge-enabled {{
            background: #d1fae5;
            color: #065f46;
        }}
        
        .badge-disabled {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .badge-strategy {{
            background: #dbeafe;
            color: #0c4a6e;
        }}
        
        /* ============================================================= */
        /* PERCENTAGE CONTROL */
        /* ============================================================= */
        .percentage-control {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .percentage-slider {{
            flex: 1;
            min-width: 150px;
        }}
        
        .percentage-slider input {{
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: #e5e7eb;
            outline: none;
            -webkit-appearance: none;
        }}
        
        .percentage-slider input::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #667eea;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .percentage-slider input::-moz-range-thumb {{
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #667eea;
            cursor: pointer;
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .percentage-display {{
            min-width: 50px;
            text-align: right;
            font-weight: 600;
            color: #667eea;
        }}
        
        /* ============================================================= */
        /* ACTION BUTTONS */
        /* ============================================================= */
        .action-buttons {{
            display: flex;
            gap: 8px;
            justify-content: flex-end;
        }}
        
        .action-buttons button {{
            padding: 6px 12px;
            font-size: 12px;
            min-width: auto;
        }}
        
        /* ============================================================= */
        /* MODAL */
        /* ============================================================= */
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
        }}
        
        .modal.active {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .modal-content {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        
        .modal-header {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
        }}
        
        .modal-body {{
            margin-bottom: 25px;
        }}
        
        .form-group {{
            margin-bottom: 15px;
        }}
        
        .form-group label {{
            display: block;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 6px;
            color: #333;
        }}
        
        .form-group input,
        .form-group select,
        .form-group textarea {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
        }}
        
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        
        .modal-footer {{
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }}
        
        /* ============================================================= */
        /* LOADING & STATUS */
        /* ============================================================= */
        .loading {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
        
        .spinner {{
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 4px solid #f3f4f6;
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        
        .alert {{
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        
        .alert-success {{
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #6ee7b7;
        }}
        
        .alert-error {{
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fca5a5;
        }}
        
        /* ============================================================= */
        /* TABS */
        /* ============================================================= */
        .tabs {{
            display: flex;
            gap: 0;
            border-bottom: 2px solid #e5e7eb;
            margin-bottom: 20px;
        }}
        
        .tab-button {{
            padding: 12px 20px;
            border: none;
            background: none;
            font-size: 14px;
            font-weight: 600;
            color: #666;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            transition: all 0.2s;
        }}
        
        .tab-button.active {{
            color: #667eea;
            border-bottom-color: #667eea;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        /* ============================================================= */
        /* EMPTY STATE */
        /* ============================================================= */
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }}
        
        .empty-state-icon {{
            font-size: 48px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>🚩 Feature Flags Admin</h1>
            <p>{app_name} — Manage feature flags in real-time</p>
        </div>
    </header>
    
    <main>
        <div class="container">
            <!-- Alerts -->
            <div id="alertContainer"></div>
            
            <!-- Stats -->
            <div class="stats" id="statsContainer">
                <div class="stat-card">
                    <h3>Total Flags</h3>
                    <div class="value" id="statTotal">0</div>
                </div>
                <div class="stat-card">
                    <h3>Enabled</h3>
                    <div class="value" id="statEnabled">0</div>
                </div>
                <div class="stat-card">
                    <h3>Disabled</h3>
                    <div class="value" id="statDisabled">0</div>
                </div>
                <div class="stat-card">
                    <h3>By Strategy</h3>
                    <div class="value" id="statStrategies">-</div>
                </div>
            </div>
            
            <!-- Controls -->
            <div class="controls">
                <div class="search-box">
                    <input type="text" id="searchInput" placeholder="Search flags by name...">
                </div>
                <div class="button-group">
                    <select id="filterStrategy" class="btn-secondary" style="border: 1px solid #ddd;">
                        <option value="">All Strategies</option>
                        <option value="always_on">Always On</option>
                        <option value="always_off">Always Off</option>
                        <option value="percentage">Percentage</option>
                        <option value="user_id">User ID</option>
                        <option value="user_segment">Segment</option>
                    </select>
                    <button class="btn-primary" onclick="openCreateModal()">+ New Flag</button>
                </div>
            </div>
            
            <!-- Tabs -->
            <div class="tabs">
                <button class="tab-button active" onclick="switchTab('flags-tab')">Flags</button>
                <button class="tab-button" onclick="switchTab('history-tab')">History</button>
            </div>
            
            <!-- Flags Tab -->
            <div id="flags-tab" class="tab-content active">
                <div class="table-container">
                    <div id="flagsLoading" class="loading">
                        <div class="spinner"></div>
                    </div>
                    <div id="flagsContent" style="display: none;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Strategy</th>
                                    <th>Status</th>
                                    <th>Percentage</th>
                                    <th>Usage</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="flagsTable">
                            </tbody>
                        </table>
                    </div>
                    <div id="emptyState" style="display: none;">
                        <div class="empty-state">
                            <div class="empty-state-icon">🚩</div>
                            <h3>No flags found</h3>
                            <p>Create your first flag to get started</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- History Tab -->
            <div id="history-tab" class="tab-content">
                <div class="table-container">
                    <div id="historyLoading" class="loading">
                        <div class="spinner"></div>
                    </div>
                    <div id="historyContent" style="display: none;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Flag</th>
                                    <th>Action</th>
                                    <th>Time</th>
                                    <th>User</th>
                                </tr>
                            </thead>
                            <tbody id="historyTable">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </main>
    
    <!-- Create/Edit Modal -->
    <div id="flagModal" class="modal">
        <div class="modal-content">
            <div class="modal-header" id="modalTitle">Create New Flag</div>
            <div class="modal-body">
                <form id="flagForm">
                    <div class="form-group">
                        <label>Flag Name</label>
                        <input type="text" id="flagName" required placeholder="e.g., new_dashboard">
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea id="flagDescription" rows="2" placeholder="What does this flag control?"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Strategy</label>
                        <select id="flagStrategy" required>
                            <option value="">Select strategy</option>
                            <option value="always_on">Always On</option>
                            <option value="always_off">Always Off</option>
                            <option value="percentage">Percentage Rollout</option>
                            <option value="user_id">User ID</option>
                            <option value="user_segment">User Segment</option>
                        </select>
                    </div>
                    <div class="form-group" id="percentageGroup" style="display: none;">
                        <label>Rollout Percentage</label>
                        <input type="number" id="flagPercentage" min="0" max="100" value="50">
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn-primary" onclick="saveFlag()">Save Flag</button>
            </div>
        </div>
    </div>
    
    <script>
        // Configuration
        const API_BASE = "{api_base}";
        
        // State
        let flags = [];
        let currentEditId = null;
        
        // Initialization
        document.addEventListener('DOMContentLoaded', () => {{
            loadFlags();
            setupEventListeners();
        }});
        
        // Event Listeners
        function setupEventListeners() {{
            document.getElementById('searchInput').addEventListener('keyup', filterFlags);
            document.getElementById('filterStrategy').addEventListener('change', filterFlags);
            document.getElementById('flagStrategy').addEventListener('change', (e) => {{
                const group = document.getElementById('percentageGroup');
                group.style.display = e.target.value === 'percentage' ? 'block' : 'none';
            }});
        }}
        
        // API Calls
        async function apiCall(endpoint, options = {{}}) {{
            try {{
                const response = await fetch(API_BASE + endpoint, {{
                    headers: {{'Content-Type': 'application/json'}},
                    ...options
                }});
                
                if (!response.ok) {{
                    throw new Error(`API error: ${{response.status}}`);
                }}
                
                return await response.json();
            }} catch (error) {{
                showAlert(`Error: ${{error.message}}`, 'error');
                throw error;
            }}
        }}
        
        // Load flags
        async function loadFlags() {{
            try {{
                const data = await apiCall('/');
                updateStats(data);
                
                const flagsList = await apiCall('/flags');
                flags = flagsList;
                renderFlags(flags);
            }} catch (error) {{
                console.error('Failed to load flags:', error);
            }}
        }}
        
        // Update stats
        function updateStats(data) {{
            document.getElementById('statTotal').textContent = data.total_flags;
            document.getElementById('statEnabled').textContent = data.enabled_flags;
            document.getElementById('statDisabled').textContent = data.disabled_flags;
        }}
        
        // Render flags table
        function renderFlags(flagsToRender) {{
            const tbody = document.getElementById('flagsTable');
            const empty = document.getElementById('emptyState');
            const loading = document.getElementById('flagsLoading');
            const content = document.getElementById('flagsContent');
            
            loading.style.display = 'none';
            
            if (flagsToRender.length === 0) {{
                empty.style.display = 'block';
                content.style.display = 'none';
                return;
            }}
            
            empty.style.display = 'none';
            content.style.display = 'block';
            
            tbody.innerHTML = flagsToRender.map(flag => `
                <tr>
                    <td><strong>${{escapeHtml(flag.name)}}</strong><br><small style="color: #999;">${{escapeHtml(flag.id)}}</small></td>
                    <td><span class="badge badge-strategy">${{flag.strategy}}</span></td>
                    <td><span class="badge ${{flag.enabled ? 'badge-enabled' : 'badge-disabled'}}">${{flag.enabled ? 'Enabled' : 'Disabled'}}</span></td>
                    <td>${{flag.percentage !== null ? flag.percentage + '%' : '-'}}</td>
                    <td>${{flag.usage_count || 0}} checks</td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn-secondary" onclick="editFlag('${{flag.id}}')">Edit</button>
                            <button class="btn-danger" onclick="deleteFlag('${{flag.id}}')">Delete</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }}
        
        // Filter flags
        function filterFlags() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const strategy = document.getElementById('filterStrategy').value;
            
            const filtered = flags.filter(flag => 
                (flag.name.toLowerCase().includes(search) || flag.id.toLowerCase().includes(search)) &&
                (!strategy || flag.strategy === strategy)
            );
            
            renderFlags(filtered);
        }}
        
        // Modal functions
        function openCreateModal() {{
            currentEditId = null;
            document.getElementById('flagForm').reset();
            document.getElementById('modalTitle').textContent = 'Create New Flag';
            document.getElementById('flagModal').classList.add('active');
        }}
        
        function closeModal() {{
            document.getElementById('flagModal').classList.remove('active');
        }}
        
        // Save flag
        async function saveFlag() {{
            const name = document.getElementById('flagName').value;
            const description = document.getElementById('flagDescription').value;
            const strategy = document.getElementById('flagStrategy').value;
            const percentage = document.getElementById('flagPercentage').value;
            
            if (!name || !strategy) {{
                showAlert('Please fill in all required fields', 'error');
                return;
            }}
            
            const flagData = {{
                name,
                description,
                strategy,
                percentage: strategy === 'percentage' ? parseInt(percentage) : null,
                enabled: true
            }};
            
            try {{
                if (currentEditId) {{
                    await apiCall(`/flags/${{currentEditId}}`, {{
                        method: 'PATCH',
                        body: JSON.stringify(flagData)
                    }});
                    showAlert('Flag updated successfully', 'success');
                }} else {{
                    await apiCall('/flags', {{
                        method: 'POST',
                        body: JSON.stringify(flagData)
                    }});
                    showAlert('Flag created successfully', 'success');
                }}
                closeModal();
                loadFlags();
            }} catch (error) {{
                console.error('Failed to save flag:', error);
            }}
        }}
        
        // Edit flag
        async function editFlag(flagId) {{
            const flag = flags.find(f => f.id === flagId);
            if (flag) {{
                currentEditId = flagId;
                document.getElementById('flagName').value = flag.name;
                document.getElementById('flagDescription').value = flag.description || '';
                document.getElementById('flagStrategy').value = flag.strategy;
                document.getElementById('flagPercentage').value = flag.percentage || 50;
                document.getElementById('modalTitle').textContent = 'Edit Flag';
                document.getElementById('flagModal').classList.add('active');
            }}
        }}
        
        // Delete flag
        async function deleteFlag(flagId) {{
            if (confirm('Are you sure you want to delete this flag?')) {{
                try {{
                    await apiCall(`/flags/${{flagId}}`, {{ method: 'DELETE' }});
                    showAlert('Flag deleted successfully', 'success');
                    loadFlags();
                }} catch (error) {{
                    console.error('Failed to delete flag:', error);
                }}
            }}
        }}
        
        // Tab switching
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-button').forEach(el => el.classList.remove('active'));
            
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }}
        
        // Utilities
        function showAlert(message, type = 'success') {{
            const container = document.getElementById('alertContainer');
            const alert = document.createElement('div');
            alert.className = `alert alert-${{type}}`;
            alert.textContent = message;
            container.appendChild(alert);
            
            setTimeout(() => alert.remove(), 5000);
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});
        
        // Click outside modal to close
        document.getElementById('flagModal').addEventListener('click', (e) => {{
            if (e.target === document.getElementById('flagModal')) closeModal();
        }});
    </script>
</body>
</html>
"""
