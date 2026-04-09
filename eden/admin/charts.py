"""
Eden Admin Panel — Dashboard Chart Widgets

Provides reusable chart widgets for admin dashboards with data endpoints.

**Usage:**

    from eden.admin.charts import DashboardWidget, ChartWidget, StatWidget

    class UserCountWidget(ChartWidget):
        label = "Users Over Time"
        type = "line"  # or "bar", "pie", "doughnut"
        
        async def get_data(self):
            # Fetch data for the chart
            ...
            return {"labels": [...], "datasets": [...]}

    # Register in dashboard
    dashboard = AdminDashboard(widgets=[UserCountWidget()])
"""

import logging
from typing import Any, Dict, List, Optional, Type
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DashboardWidget(ABC):
    """Base class for dashboard widgets."""
    
    title: str = "Widget"
    description: str = ""
    width: str = "col-md-6"  # Bootstrap column width
    
    @abstractmethod
    async def render(self) -> Dict[str, Any]:
        """
        Render widget data for the dashboard.
        
        Returns:
            Dictionary with widget state and data
        """
        pass


class StatWidget(DashboardWidget):
    """Simple statistic widget displaying a single number."""
    
    def __init__(
        self,
        label: str,
        value: Any = 0,
        icon: str = "square",
        color: str = "primary",
    ):
        """
        Initialize stat widget.
        
        Args:
            label: Widget label (e.g., "Total Users")
            value: Current value to display
            icon: Icon name (Font Awesome or similar)
            color: Color class (primary, success, danger, warning, info)
        """
        self.label = label
        self.value = value
        self.icon = icon
        self.color = color
    
    async def render(self) -> Dict[str, Any]:
        """Render stat widget."""
        return {
            "type": "stat",
            "label": self.label,
            "value": self.value,
            "icon": self.icon,
            "color": self.color,
        }


class ChartWidget(DashboardWidget):
    """Chart widget with configurable chart type."""
    
    type: str = "line"  # line, bar, pie, doughnut, polar, radar
    chart_id: str = ""
    
    def __init__(self, label: str = "", type: str = "line", chart_id: str = ""):
        """
        Initialize chart widget.
        
        Args:
            label: Chart title
            type: Chart.js chart type
            chart_id: Unique identifier for the chart
        """
        self.label = label
        self.type = type
        self.chart_id = chart_id or f"chart-{id(self)}"
    
    @abstractmethod
    async def get_data(self) -> Dict[str, Any]:
        """
        Fetch and format data for the chart.
        
        Expected return format (Chart.js compatible):
        {
            "labels": ["Jan", "Feb", "Mar"],
            "datasets": [
                {
                    "label": "Series 1",
                    "data": [10, 20, 30],
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "borderColor": "rgb(75, 192, 192)",
                }
            ]
        }
        """
        pass
    
    async def render(self) -> Dict[str, Any]:
        """Render chart widget."""
        data = await self.get_data()
        return {
            "type": "chart",
            "chart_id": self.chart_id,
            "chart_type": self.type,
            "label": self.label,
            "data": data,
        }


class LineChartWidget(ChartWidget):
    """Line chart widget."""
    
    def __init__(self, label: str = "", chart_id: str = ""):
        super().__init__(label, type="line", chart_id=chart_id)


class BarChartWidget(ChartWidget):
    """Bar chart widget."""
    
    def __init__(self, label: str = "", chart_id: str = ""):
        super().__init__(label, type="bar", chart_id=chart_id)


class PieChartWidget(ChartWidget):
    """Pie chart widget."""
    
    def __init__(self, label: str = "", chart_id: str = ""):
        super().__init__(label, type="pie", chart_id=chart_id)


class TableWidget(DashboardWidget):
    """Data table widget for displaying records."""
    
    def __init__(
        self,
        label: str = "Data",
        columns: Optional[List[str]] = None,
        rows: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize table widget.
        
        Args:
            label: Table title
            columns: List of column names
            rows: List of row data dictionaries
        """
        self.label = label
        self.columns = columns or []
        self.rows = rows or []
    
    async def render(self) -> Dict[str, Any]:
        """Render table widget."""
        return {
            "type": "table",
            "label": self.label,
            "columns": self.columns,
            "rows": self.rows,
        }


class TimeSeriesChartWidget(ChartWidget):
    """Time series chart showing data over time."""
    
    async def get_time_series_data(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Generate time series labels and empty datasets.
        
        Args:
            days: Number of days to show
        
        Returns:
            Dictionary with date labels ready for data
        """
        labels = []
        end_date = datetime.now()
        
        for i in range(days, 0, -1):
            date = end_date - timedelta(days=i)
            labels.append(date.strftime("%Y-%m-%d"))
        
        return {
            "labels": labels,
            "datasets": []
        }


class DashboardWidgetRegistry:
    """Registry for managing dashboard widgets."""
    
    _widgets: Dict[str, Type[DashboardWidget]] = {}
    
    @classmethod
    def register(cls, name: str, widget_class: Type[DashboardWidget]) -> None:
        """Register a widget class."""
        cls._widgets[name] = widget_class
        logger.debug(f"Registered dashboard widget: {name}")
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[DashboardWidget]]:
        """Get a registered widget class."""
        return cls._widgets.get(name)
    
    @classmethod
    def list_widgets(cls) -> List[str]:
        """List all registered widget names."""
        return list(cls._widgets.keys())


# Built-in widget registry
DashboardWidgetRegistry.register("stat", StatWidget)
DashboardWidgetRegistry.register("chart", ChartWidget)
DashboardWidgetRegistry.register("line_chart", LineChartWidget)
DashboardWidgetRegistry.register("bar_chart", BarChartWidget)
DashboardWidgetRegistry.register("pie_chart", PieChartWidget)
DashboardWidgetRegistry.register("table", TableWidget)
DashboardWidgetRegistry.register("time_series", TimeSeriesChartWidget)


class AdminDashboard:
    """Aggregates dashboard widgets."""
    
    def __init__(self, widgets: Optional[List[DashboardWidget]] = None):
        """
        Initialize dashboard.
        
        Args:
            widgets: List of widget instances
        """
        self.widgets = widgets or []
    
    def add_widget(self, widget: DashboardWidget) -> None:
        """Add a widget to the dashboard."""
        self.widgets.append(widget)
    
    async def render_all(self) -> List[Dict[str, Any]]:
        """Render all widgets."""
        rendered = []
        for widget in self.widgets:
            try:
                data = await widget.render()
                rendered.append(data)
            except Exception as e:
                logger.error(f"Failed to render widget {widget}: {e}", exc_info=True)
        return rendered


# Example implementations for common use cases

class ModelCountWidget(StatWidget):
    """Widget showing count of a model."""
    
    def __init__(self, model: Type, label: str = "", icon: str = "database"):
        """
        Initialize model count widget.
        
        Args:
            model: The model class to count
            label: Widget label (defaults to model name)
            icon: Icon name
        """
        self.model = model
        label = label or f"Total {getattr(model, '__name__', 'Records')}"
        super().__init__(label=label, icon=icon)
    
    async def render(self) -> Dict[str, Any]:
        """Render with actual model count."""
        try:
            count = await self.model.count()
            self.value = count
        except Exception as e:
            logger.warning(f"Failed to count {self.model}: {e}")
            self.value = 0
        
        return await super().render()


class RecentActivityWidget(TableWidget):
    """Widget showing recent activity/audit log."""
    
    def __init__(self, limit: int = 10):
        """
        Initialize activity widget.
        
        Args:
            limit: Number of recent activities to show
        """
        super().__init__(
            label="Recent Activity",
            columns=["timestamp", "user", "action", "model"]
        )
        self.limit = limit
    
    async def render(self) -> Dict[str, Any]:
        """Render with actual recent activity."""
        try:
            from eden.admin.models import AuditLog
            
            logs = await AuditLog.query().order_by("-timestamp").limit(self.limit).all()
            self.rows = [
                {
                    "timestamp": str(log.timestamp)[:16],
                    "user": str(log.user_id)[:8] if log.user_id else "system",
                    "action": log.action,
                    "model": log.model_name,
                }
                for log in logs
            ]
        except Exception as e:
            logger.warning(f"Failed to load recent activity: {e}")
            self.rows = []
        
        return await super().render()
