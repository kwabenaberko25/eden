"""
Login page template for admin dashboard authentication.

Provides a secure, offline-capable login UI with:
- Email/password authentication
- Remember me option
- Error message display
- Responsive design matching dashboard theme
"""


class LoginPageTemplate:
    """Self-contained login page template."""
    
    @staticmethod
    def render(app_name: str = "Eden Framework", login_url: str = "/admin/login") -> str:
        """
        Render login page HTML.
        
        Args:
            app_name: Application name
            login_url: URL for login form submission
            
        Returns:
            Complete login page HTML
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - {app_name}</title>
    <style>
        /* ============================================================= */
        /* RESET & BASE */
        /* ============================================================= */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html, body {{
            height: 100%;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        /* ============================================================= */
        /* LOGIN CONTAINER */
        /* ============================================================= */
        .login-container {{
            width: 100%;
            max-width: 420px;
            padding: 20px;
        }}
        
        .login-card {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            animation: slideUp 0.4s ease-out;
        }}
        
        @keyframes slideUp {{
            from {{
                opacity: 0;
                transform: translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        /* ============================================================= */
        /* HEADER */
        /* ============================================================= */
        .login-header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .login-logo {{
            font-size: 48px;
            margin-bottom: 15px;
        }}
        
        .login-header h1 {{
            font-size: 24px;
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }}
        
        .login-header p {{
            font-size: 14px;
            color: #999;
        }}
        
        /* ============================================================= */
        /* FORM */
        /* ============================================================= */
        .login-form {{
            margin-bottom: 20px;
        }}
        
        .form-group {{
            margin-bottom: 20px;
        }}
        
        .form-group label {{
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .form-group input {{
            width: 100%;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
            transition: all 0.2s;
        }}
        
        .form-group input:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        
        .form-group input::placeholder {{
            color: #ccc;
        }}
        
        /* ============================================================= */
        /* REMEMBER ME */
        /* ============================================================= */
        .remember-me {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        
        .remember-me input {{
            width: 18px;
            height: 18px;
            cursor: pointer;
        }}
        
        .remember-me label {{
            cursor: pointer;
            color: #666;
            margin: 0;
            font-weight: 500;
        }}
        
        /* ============================================================= */
        /* BUTTONS */
        /* ============================================================= */
        .login-button {{
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .login-button:hover {{
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
            transform: translateY(-2px);
        }}
        
        .login-button:active {{
            transform: translateY(0);
        }}
        
        .login-button:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
        }}
        
        /* ============================================================= */
        /* ALERTS */
        /* ============================================================= */
        .alert {{
            padding: 12px 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
            animation: slideDown 0.3s ease-out;
        }}
        
        @keyframes slideDown {{
            from {{
                opacity: 0;
                transform: translateY(-10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .alert-error {{
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fca5a5;
        }}
        
        .alert-success {{
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #6ee7b7;
        }}
        
        /* ============================================================= */
        /* LOADING STATE */
        /* ============================================================= */
        .spinner {{
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 8px;
            vertical-align: middle;
        }}
        
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        
        /* ============================================================= */
        /* FOOTER */
        /* ============================================================= */
        .login-footer {{
            text-align: center;
            font-size: 12px;
            color: #999;
            margin-top: 30px;
        }}
        
        .login-footer a {{
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }}
        
        .login-footer a:hover {{
            text-decoration: underline;
        }}
        
        /* ============================================================= */
        /* RESPONSIVE */
        /* ============================================================= */
        @media (max-width: 480px) {{
            .login-card {{
                padding: 30px 20px;
            }}
            
            .login-header h1 {{
                font-size: 20px;
            }}
            
            .login-logo {{
                font-size: 40px;
            }}
        }}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-card">
            <!-- Header -->
            <div class="login-header">
                <div class="login-logo">🔐</div>
                <h1>Admin Login</h1>
                <p>{app_name}</p>
            </div>
            
            <!-- Alerts -->
            <div id="alertContainer"></div>
            
            <!-- Login Form -->
            <form class="login-form" onsubmit="handleLogin(event)">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input
                        type="text"
                        id="username"
                        name="username"
                        placeholder="Enter your username"
                        required
                        autocomplete="username"
                        autofocus
                    />
                </div>
                
                <div class="form-group">
                    <label for="password">Password</label>
                    <input
                        type="password"
                        id="password"
                        name="password"
                        placeholder="Enter your password"
                        required
                        autocomplete="current-password"
                    />
                </div>
                
                <div class="remember-me">
                    <input type="checkbox" id="remember" name="remember" />
                    <label for="remember">Remember me</label>
                </div>
                
                <button type="submit" class="login-button" id="loginButton">
                    Sign In
                </button>
            </form>
            
            <!-- Footer -->
            <div class="login-footer">
                <p>© 2024 {app_name}</p>
            </div>
        </div>
    </div>
    
    <script>
        const LOGIN_URL = "{login_url}";
        const REDIRECT_URL = "/admin";
        
        // Load saved username if remember me was checked
        window.addEventListener('DOMContentLoaded', () => {{
            const saved_username = localStorage.getItem('admin_username');
            if (saved_username) {{
                document.getElementById('username').value = saved_username;
                document.getElementById('remember').checked = true;
            }}
        }});
        
        async function handleLogin(event) {{
            event.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const remember = document.getElementById('remember').checked;
            
            const button = document.getElementById('loginButton');
            const originalText = button.innerHTML;
            
            try {{
                // Show loading state
                button.disabled = true;
                button.innerHTML = '<span class="spinner"></span>Signing in...';
                
                // Call login API
                const response = await fetch(LOGIN_URL, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{ username, password }})
                }});
                
                const data = await response.json();
                
                if (!response.ok) {{
                    showAlert(data.detail || 'Login failed', 'error');
                    button.disabled = false;
                    button.innerHTML = originalText;
                    return;
                }}
                
                // Save token
                localStorage.setItem('admin_token', data.access_token);
                
                // Save username if remember me
                if (remember) {{
                    localStorage.setItem('admin_username', username);
                }} else {{
                    localStorage.removeItem('admin_username');
                }}
                
                // Show success
                showAlert('Login successful! Redirecting...', 'success');
                
                // Redirect after 500ms
                setTimeout(() => {{
                    window.location.href = REDIRECT_URL;
                }}, 500);
                
            }} catch (error) {{
                showAlert('Network error: ' + error.message, 'error');
                button.disabled = false;
                button.innerHTML = originalText;
            }}
        }}
        
        function showAlert(message, type = 'error') {{
            const container = document.getElementById('alertContainer');
            const alert = document.createElement('div');
            alert.className = `alert alert-${{type}}`;
            alert.textContent = message;
            container.appendChild(alert);
            
            // Auto-remove after 5 seconds
            setTimeout(() => alert.remove(), 5000);
        }}
        
        // Clear alerts when typing
        document.getElementById('username').addEventListener('focus', clearAlerts);
        document.getElementById('password').addEventListener('focus', clearAlerts);
        
        function clearAlerts() {{
            document.getElementById('alertContainer').innerHTML = '';
        }}
        
        // Enter key submits form
        document.getElementById('password').addEventListener('keypress', (e) => {{
            if (e.key === 'Enter') {{
                document.querySelector('form').dispatchEvent(new Event('submit'));
            }}
        }});
    </script>
</body>
</html>
"""
