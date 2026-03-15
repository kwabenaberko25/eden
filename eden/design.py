"""
Eden — Premium Design System

Provides design tokens (colors, typography, spacing, shadows) as Python
constants and Jinja2 filters for consistent styling across all templates.
"""


# ── Color Palette ─────────────────────────────────────────────────────────────

COLORS = {
    # Backgrounds
    "obsidian":      "#0F172A",
    "surface":       "#1E293B",
    "surface_light": "#334155",
    "overlay":       "rgba(30, 41, 59, 0.9)",

    # Primary
    "primary":       "#2563EB",
    "primary_light": "#3B82F6",
    "primary_dark":  "#1D4ED8",

    # Success
    "success":       "#10B981",
    "success_light": "#34D399",
    "success_dark":  "#059669",

    # Warning
    "warning":       "#F59E0B",
    "warning_light": "#FBBF24",
    "warning_dark":  "#D97706",

    # Danger
    "danger":        "#EF4444",
    "danger_light":  "#F87171",
    "danger_dark":   "#DC2626",

    # Grey / Slate
    "slate_50":      "#F8FAFC",
    "slate_100":     "#F1F5F9",
    "slate_200":     "#E2E8F0",
    "slate_300":     "#CBD5E1",
    "slate_400":     "#94A3B8",
    "slate_500":     "#64748B",
    "slate_600":     "#475569",
    "slate_700":     "#334155",
    "slate_800":     "#1E293B",
    "slate_900":     "#0F172A",

    # Accents
    "purple":        "#8B5CF6",
    "pink":          "#EC4899",
    "cyan":          "#06B6D4",
}

# ── Tailwind Utility Mappings ─────────────────────────────────────────────────

BG_MAP = {
    "primary":   "bg-blue-600",
    "secondary": "bg-slate-700",
    "success":   "bg-emerald-500",
    "warning":   "bg-amber-500",
    "danger":    "bg-red-500",
    "surface":   "bg-gray-800/90",
    "obsidian":  "bg-[#0F172A]",
    "muted":     "bg-slate-800",
}

TEXT_MAP = {
    "primary":   "text-blue-400",
    "secondary": "text-slate-300",
    "muted":     "text-slate-400",
    "success":   "text-emerald-400",
    "warning":   "text-amber-400",
    "danger":    "text-red-400",
    "heading":   "text-slate-100",
    "body":      "text-slate-200",
    "dim":       "text-slate-500",
}

BORDER_MAP = {
    "default":   "border-gray-700",
    "primary":   "border-blue-500",
    "success":   "border-emerald-500",
    "warning":   "border-amber-500",
    "danger":    "border-red-500",
    "subtle":    "border-gray-700/50",
    "muted":     "border-slate-600",
}

SHADOW_MAP = {
    "primary":   "shadow-blue-500/20",
    "success":   "shadow-emerald-500/20",
    "warning":   "shadow-amber-500/20",
    "danger":    "shadow-red-500/20",
    "none":      "shadow-none",
    "default":   "shadow-lg shadow-black/20",
}

# ── Typography ────────────────────────────────────────────────────────────────

FONTS = {
    "primary": "'Plus Jakarta Sans', sans-serif",
    "heading": "'Outfit', 'Plus Jakarta Sans', sans-serif",
    "mono":    "'JetBrains Mono', monospace",
}

# ── Spacing (base 0.25rem) ────────────────────────────────────────────────────

def spacing(units: int) -> str:
    """Convert spacing units to rem. ``spacing(4)`` → ``1rem``."""
    val = units * 0.25
    if val == int(val):
        return f"{int(val)}rem"
    return f"{val}rem"


# ── Jinja2 Filters ───────────────────────────────────────────────────────────

def eden_color(name: str) -> str:
    """Resolve a design-system color name to its hex value."""
    return COLORS.get(name, name)


def eden_bg(name: str) -> str:
    """Resolve to a Tailwind background utility class."""
    return BG_MAP.get(name, f"bg-{name}")


def eden_text(name: str) -> str:
    """Resolve to a Tailwind text-color utility class."""
    return TEXT_MAP.get(name, f"text-{name}")


def eden_border(name: str) -> str:
    """Resolve to a Tailwind border-color utility class."""
    return BORDER_MAP.get(name, f"border-{name}")


def eden_shadow(name: str) -> str:
    """Resolve to a Tailwind shadow utility class."""
    return SHADOW_MAP.get(name, f"shadow-{name}")


def eden_font(name: str) -> str:
    """Resolve a font-family name."""
    return FONTS.get(name, name)
