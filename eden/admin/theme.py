"""
Eden Admin — Design System & Themeing

Defines the premium look and feel for the Elite Admin Panel.
Uses CSS variables and utility classes for a consistent UI.
"""

from dataclasses import dataclass, field


@dataclass
class AdminTheme:
    """Design tokens for the Eden Elite Admin Panel."""
    
    # Primary Colors (Sleek Indigo/Violet)
    primary: str = "#6366f1"
    primary_hover: str = "#4f46e5"
    primary_light: str = "#eef2ff"
    
    # Neutral Colors (Slate)
    bg_main: str = "#0f172a"
    bg_card: str = "#1e293b"
    text_main: str = "#f8fafc"
    text_muted: str = "#94a3b8"
    border: str = "#334155"
    
    # Success/Error/Warning
    success: str = "#10b981"
    error: str = "#ef4444"
    warning: str = "#f59e0b"
    
    # Sidebar
    sidebar_bg: str = "#0f172a"
    sidebar_text: str = "#94a3b8"
    sidebar_text_active: str = "#ffffff"
    sidebar_accent: str = "#1e293b"

    def to_css(self) -> str:
        """Generates root CSS variables for transparency and ease of use in templates."""
        return f"""
        :root {{
            --eden-primary: {self.primary};
            --eden-primary-hover: {self.primary_hover};
            --eden-primary-light: {self.primary_light};
            --eden-primary-rgb: 99, 102, 241;
            --eden-bg-main: {self.bg_main};
            --eden-bg-card: {self.bg_card};
            --eden-text-main: {self.text_main};
            --eden-text-muted: {self.text_muted};
            --eden-border: {self.border};
            --eden-success: {self.success};
            --eden-error: {self.error};
            --eden-error-rgb: 239, 68, 68;
            --eden-warning: {self.warning};
            --eden-sidebar-bg: {self.sidebar_bg};
            --eden-sidebar-text: {self.sidebar_text};
            --eden-sidebar-text-active: {self.sidebar_text_active};
            --eden-sidebar-accent: {self.sidebar_accent};
            --eden-radius: 1rem;
            --eden-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
            
            /* Compatibility Aliases for admin.css */
            --eden-surface: {self.bg_main};
            --eden-on-surface: {self.text_main};
            --eden-on-surface-variant: {self.text_muted};
            --eden-surface-container: {self.bg_card};
            --eden-surface-container-low: {self.bg_main};
            --eden-surface-container-high: {self.sidebar_accent};
            --eden-outline: {self.border};
            --eden-outline-variant: {self.border};
        }}
        """

# Default global theme
default_theme = AdminTheme()
