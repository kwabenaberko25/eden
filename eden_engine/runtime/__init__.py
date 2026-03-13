"""
Eden Template Runtime

Executes compiled templates with filters, tests, and directives.

Components:
  - TemplateContext: Variable scoping
  - TemplateEngine: Main execution engine
  - DirectiveHandler: Base for directive implementations
  - FilterRegistry: 38+ filters
  - TestRegistry: 12+ test functions
"""

from .engine import (
    TemplateContext,
    TemplateEngine,
    DirectiveHandler,
    FilterRegistry,
    TestRegistry,
    SafeExpressionEvaluator,
)

from .directives import (
    IfHandler, UnlessHandler, ForHandler, ForeachHandler,
    SwitchHandler, CaseHandler, BreakHandler, ContinueHandler,
    ComponentHandler, SlotHandler, RenderFieldHandler, PropsHandler,
    ExtendsHandler, BlockHandler, YieldHandler, SectionHandler,
    PushHandler, SuperHandler,
    CsrfHandler, CheckedHandler, SelectedHandler, DisabledHandler,
    ReadonlyHandler, ErrorHandler,
    UrlHandler, ActiveLinkHandler, RouteHandler,
    AuthHandler, GuestHandler, HtmxHandler, NonHtmxHandler,
    CssHandler, JsHandler, ViteHandler,
    LetHandler, DumpHandler, SpanHandler, MessagesHandler,
    FlashHandler, StatusHandler,
    IncludeHandler, FragmentHandler,
    MethodHandler, OldHandler, JsonHandler,
    create_all_directive_handlers,
)

__all__ = [
    # Engine
    'TemplateContext',
    'TemplateEngine',
    'DirectiveHandler',
    'FilterRegistry',
    'TestRegistry',
    'SafeExpressionEvaluator',
    
    # All directive handlers
    'IfHandler', 'UnlessHandler', 'ForHandler', 'ForeachHandler',
    'SwitchHandler', 'CaseHandler', 'BreakHandler', 'ContinueHandler',
    'ComponentHandler', 'SlotHandler', 'RenderFieldHandler', 'PropsHandler',
    'ExtendsHandler', 'BlockHandler', 'YieldHandler', 'SectionHandler',
    'PushHandler', 'SuperHandler',
    'CsrfHandler', 'CheckedHandler', 'SelectedHandler', 'DisabledHandler',
    'ReadonlyHandler', 'ErrorHandler',
    'UrlHandler', 'ActiveLinkHandler', 'RouteHandler',
    'AuthHandler', 'GuestHandler', 'HtmxHandler', 'NonHtmxHandler',
    'CssHandler', 'JsHandler', 'ViteHandler',
    'LetHandler', 'DumpHandler', 'SpanHandler', 'MessagesHandler',
    'FlashHandler', 'StatusHandler',
    'IncludeHandler', 'FragmentHandler',
    'MethodHandler', 'OldHandler', 'JsonHandler',
    
    # Utilities
    'create_all_directive_handlers',
]
