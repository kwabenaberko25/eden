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
    bg_main: str = "#f8fafc"
    bg_card: str = "#ffffff"
    text_main: str = "#1e293b"
    text_muted: str = "#64748b"
    border: str = "#e2e8f0"
    
    # Success/Error/Warning
    success: str = "#10b981"
    error: str = "#ef4444"
    warning: str = "#f59e0b"
    
    # Sidebar
    sidebar_bg: str = "#1e293b"
    sidebar_text: str = "#94a3b8"
    sidebar_text_active: str = "#ffffff"
    sidebar_accent: str = "#334155"

    def to_css(self) -> str:
        """Generates root CSS variables for transparency and ease of use in templates."""
        return f"""
        :root {{
            --eden-primary: {self.primary};
            --eden-primary-hover: {self.primary_hover};
            --eden-primary-light: {self.primary_light};
            --eden-bg-main: {self.bg_main};
            --eden-bg-card: {self.bg_card};
            --eden-text-main: {self.text_main};
            --eden-text-muted: {self.text_muted};
            --eden-border: {self.border};
            --eden-success: {self.success};
            --eden-error: {self.error};
            --eden-warning: {self.warning};
            --eden-sidebar-bg: {self.sidebar_bg};
            --eden-sidebar-text: {self.sidebar_text};
            --eden-sidebar-text-active: {self.sidebar_text_active};
            --eden-sidebar-accent: {self.sidebar_accent};
            --eden-radius: 0.75rem;
            --eden-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        }}
        """

# Default global theme
default_theme = AdminTheme()
