"""
Eden Directive Handlers

Implementation of all 40+ directives for template rendering.

Directives organized by category:
  - Control Flow (8)
  - Components (4) 
  - Inheritance (6)
  - Forms (6)
  - Routing (3)
  - Auth (4)
  - Assets (3)
  - Data (6)
  - Special (2)
  - Meta (3)
"""

import asyncio
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from .engine import DirectiveHandler, TemplateContext


# ================= Control Flow Directives =================

class IfHandler(DirectiveHandler):
    """Handle @if(condition) { body } directive."""
    
    def __init__(self):
        super().__init__('if')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute if directive."""
        # Implementation handled by code generator
        return ""


class UnlessHandler(DirectiveHandler):
    """Handle @unless(condition) { body } directive."""
    
    def __init__(self):
        super().__init__('unless')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute unless directive."""
        return ""


class ForHandler(DirectiveHandler):
    """Handle @for(i = 0; i < 10; i++) { body } directive."""
    
    def __init__(self):
        super().__init__('for')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute for directive."""
        return ""


class ForeachHandler(DirectiveHandler):
    """Handle @foreach(items as item) { body } directive."""
    
    def __init__(self):
        super().__init__('foreach')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute foreach directive."""
        return ""


class SwitchHandler(DirectiveHandler):
    """Handle @switch(value) { @case(1) ... } directive."""
    
    def __init__(self):
        super().__init__('switch')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute switch directive."""
        return ""


class CaseHandler(DirectiveHandler):
    """Handle @case(value) { body } inside switch."""
    
    def __init__(self):
        super().__init__('case')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute case directive."""
        return ""


class BreakHandler(DirectiveHandler):
    """Handle @break directive."""
    
    def __init__(self):
        super().__init__('break')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute break directive."""
        return ""


class ContinueHandler(DirectiveHandler):
    """Handle @continue directive."""
    
    def __init__(self):
        super().__init__('continue')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute continue directive."""
        return ""


# ================= Component Directives =================

class ComponentHandler(DirectiveHandler):
    """Handle @component('name', props) { @slot('name') } directive."""
    
    def __init__(self):
        super().__init__('component')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute component directive."""
        return ""


class SlotHandler(DirectiveHandler):
    """Handle @slot('name') { default content } inside component."""
    
    def __init__(self):
        super().__init__('slot')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute slot directive."""
        return ""


class RenderFieldHandler(DirectiveHandler):
    """Handle @render_field(field) directive."""
    
    def __init__(self):
        super().__init__('render_field')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute render_field directive."""
        return ""


class PropsHandler(DirectiveHandler):
    """Handle @props(attributes) { body } directive."""
    
    def __init__(self):
        super().__init__('props')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute props directive."""
        return ""


# ================= Inheritance Directives =================

class ExtendsHandler(DirectiveHandler):
    """Handle @extends('template') directive."""
    
    def __init__(self):
        super().__init__('extends')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute extends directive."""
        return ""


class BlockHandler(DirectiveHandler):
    """Handle @block('name') { content } directive."""
    
    def __init__(self):
        super().__init__('block')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute block directive."""
        return ""


class YieldHandler(DirectiveHandler):
    """Handle @yield('name') directive."""
    
    def __init__(self):
        super().__init__('yield')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute yield directive."""
        return ""


class SectionHandler(DirectiveHandler):
    """Handle @section('name') { content } directive."""
    
    def __init__(self):
        super().__init__('section')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute section directive."""
        return ""


class PushHandler(DirectiveHandler):
    """Handle @push('stack') { content } directive."""
    
    def __init__(self):
        super().__init__('push')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute push directive."""
        return ""


class SuperHandler(DirectiveHandler):
    """Handle @super directive (render parent block)."""
    
    def __init__(self):
        super().__init__('super')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute super directive."""
        return ""


# ================= Form Directives =================

class CsrfHandler(DirectiveHandler):
    """Handle @csrf directive (output CSRF token)."""
    
    def __init__(self):
        super().__init__('csrf')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute csrf directive."""
        csrf_token = context.get('csrf_token', '')
        return f'<input type="hidden" name="_token" value="{csrf_token}">'


class CheckedHandler(DirectiveHandler):
    """Handle @checked(field, value) directive."""
    
    def __init__(self):
        super().__init__('checked')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute checked directive."""
        field_value = context.get(kwargs.get('field'))
        check_value = kwargs.get('value')
        if field_value == check_value:
            return ' checked'
        return ''


class SelectedHandler(DirectiveHandler):
    """Handle @selected(field, value) directive."""
    
    def __init__(self):
        super().__init__('selected')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute selected directive."""
        field_value = context.get(kwargs.get('field'))
        option_value = kwargs.get('value')
        if field_value == option_value:
            return ' selected'
        return ''


class DisabledHandler(DirectiveHandler):
    """Handle @disabled(condition) directive."""
    
    def __init__(self):
        super().__init__('disabled')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute disabled directive."""
        if kwargs.get('condition'):
            return ' disabled'
        return ''


class ReadonlyHandler(DirectiveHandler):
    """Handle @readonly(condition) directive."""
    
    def __init__(self):
        super().__init__('readonly')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute readonly directive."""
        if kwargs.get('condition'):
            return ' readonly'
        return ''


class ErrorHandler(DirectiveHandler):
    """Handle @error('field') { body } directive."""
    
    def __init__(self):
        super().__init__('error')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute error directive."""
        field_name = kwargs.get('field')
        errors = context.get('errors', {})
        if field_name and field_name in errors:
            return f'<span class="error">{errors[field_name]}</span>'
        return ''


# ================= Routing Directives =================

class UrlHandler(DirectiveHandler):
    """Handle @url('route', params) directive."""
    
    def __init__(self):
        super().__init__('url')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute url directive."""
        route = kwargs.get('route', '/')
        return f"/routes/{route}"


class ActiveLinkHandler(DirectiveHandler):
    """Handle @active_link('route') directive."""
    
    def __init__(self):
        super().__init__('active_link')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute active_link directive."""
        route = kwargs.get('route', '')
        current_route = context.get('current_route', '')
        if current_route == route:
            return ' active'
        return ''


class RouteHandler(DirectiveHandler):
    """Handle @route('name') directive."""
    
    def __init__(self):
        super().__init__('route')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute route directive."""
        return ""


# ================= Authentication Directives =================

class AuthHandler(DirectiveHandler):
    """Handle @auth { body } directive (render if authenticated)."""
    
    def __init__(self):
        super().__init__('auth')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute auth directive."""
        if context.get('authenticated', False):
            return kwargs.get('body', '')
        return ''


class GuestHandler(DirectiveHandler):
    """Handle @guest { body } directive (render if not authenticated)."""
    
    def __init__(self):
        super().__init__('guest')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute guest directive."""
        if not context.get('authenticated', True):
            return kwargs.get('body', '')
        return ''


class HtmxHandler(DirectiveHandler):
    """Handle @htmx { body } directive (render if HTMX request)."""
    
    def __init__(self):
        super().__init__('htmx')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute htmx directive."""
        if context.get('htmx_request', False):
            return kwargs.get('body', '')
        return ''


class NonHtmxHandler(DirectiveHandler):
    """Handle @non_htmx { body } directive (render if not HTMX request)."""
    
    def __init__(self):
        super().__init__('non_htmx')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute non_htmx directive."""
        if not context.get('htmx_request', True):
            return kwargs.get('body', '')
        return ''


# ================= Asset Directives =================

class CssHandler(DirectiveHandler):
    """Handle @css('path') directive."""
    
    def __init__(self):
        super().__init__('css')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute css directive."""
        path = kwargs.get('path', '')
        return f'<link rel="stylesheet" href="{path}">'


class JsHandler(DirectiveHandler):
    """Handle @js('path') directive."""
    
    def __init__(self):
        super().__init__('js')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute js directive."""
        path = kwargs.get('path', '')
        return f'<script src="{path}"></script>'


class ViteHandler(DirectiveHandler):
    """Handle @vite('entry') directive."""
    
    def __init__(self):
        super().__init__('vite')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute vite directive."""
        entry = kwargs.get('entry', '')
        return f'<script type="module" src="/vite/{entry}"></script>'


# ================= Data Directives =================

class LetHandler(DirectiveHandler):
    """Handle @let(variable = value) directive."""
    
    def __init__(self):
        super().__init__('let')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute let directive."""
        name = kwargs.get('name', '')
        value = kwargs.get('value', '')
        context.set(name, value)
        return ''


class DumpHandler(DirectiveHandler):
    """Handle @dump(variable) directive (debug output)."""
    
    def __init__(self):
        super().__init__('dump')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute dump directive."""
        var_name = kwargs.get('variable', '')
        value = context.get(var_name)
        return f'<pre class="debug">{repr(value)}</pre>'


class SpanHandler(DirectiveHandler):
    """Handle @span(text) directive."""
    
    def __init__(self):
        super().__init__('span')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute span directive."""
        text = kwargs.get('text', '')
        return f'<span>{text}</span>'


class MessagesHandler(DirectiveHandler):
    """Handle @messages { body } directive (iterate messages)."""
    
    def __init__(self):
        super().__init__('messages')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute messages directive."""
        messages = context.get('messages', [])
        output = []
        for msg in messages:
            context.set('message', msg)
            output.append(kwargs.get('body', ''))
        return ''.join(output)


class FlashHandler(DirectiveHandler):
    """Handle @flash directive (flash message)."""
    
    def __init__(self):
        super().__init__('flash')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute flash directive."""
        flash_msg = context.get('flash_message', '')
        if flash_msg:
            return f'<div class="flash">{flash_msg}</div>'
        return ''


class StatusHandler(DirectiveHandler):
    """Handle @status(code) { body } directive."""
    
    def __init__(self):
        super().__init__('status')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute status directive."""
        status_code = kwargs.get('code')
        current_status = context.get('status_code')
        if current_status == status_code:
            return kwargs.get('body', '')
        return ''


# ================= Special Directives =================

class IncludeHandler(DirectiveHandler):
    """Handle @include('template') directive."""
    
    def __init__(self):
        super().__init__('include')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute include directive."""
        template_name = kwargs.get('template', '')
        return f"<!-- Include {template_name} -->"


class FragmentHandler(DirectiveHandler):
    """Handle @fragment { body } directive."""
    
    def __init__(self):
        super().__init__('fragment')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute fragment directive."""
        return kwargs.get('body', '')


# ================= Meta Directives =================

class MethodHandler(DirectiveHandler):
    """Handle @method('POST') directive (form method spoof)."""
    
    def __init__(self):
        super().__init__('method')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute method directive."""
        method = kwargs.get('method', 'GET').upper()
        if method in ('PUT', 'PATCH', 'DELETE'):
            return f'<input type="hidden" name="_method" value="{method}">'
        return ''


class OldHandler(DirectiveHandler):
    """Handle @old('field') directive (restore old form value)."""
    
    def __init__(self):
        super().__init__('old')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute old directive."""
        field_name = kwargs.get('field', '')
        old_values = context.get('old', {})
        if field_name in old_values:
            return str(old_values[field_name])
        return ''


class JsonHandler(DirectiveHandler):
    """Handle @json(variable) directive."""
    
    def __init__(self):
        super().__init__('json')
    
    async def execute(self, context: TemplateContext, **kwargs) -> str:
        """Execute json directive."""
        import json
        var_name = kwargs.get('variable', '')
        value = context.get(var_name)
        try:
            return json.dumps(value)
        except (TypeError, ValueError):
            return 'null'


# ================= Directive Registry =================

def create_all_directive_handlers() -> Dict[str, DirectiveHandler]:
    """Create all 40+ directive handlers."""
    return {
        # Control Flow (8)
        'if': IfHandler(),
        'unless': UnlessHandler(),
        'for': ForHandler(),
        'foreach': ForeachHandler(),
        'switch': SwitchHandler(),
        'case': CaseHandler(),
        'break': BreakHandler(),
        'continue': ContinueHandler(),
        
        # Components (4)
        'component': ComponentHandler(),
        'slot': SlotHandler(),
        'render_field': RenderFieldHandler(),
        'props': PropsHandler(),
        
        # Inheritance (6)
        'extends': ExtendsHandler(),
        'block': BlockHandler(),
        'yield': YieldHandler(),
        'section': SectionHandler(),
        'push': PushHandler(),
        'super': SuperHandler(),
        
        # Forms (6)
        'csrf': CsrfHandler(),
        'checked': CheckedHandler(),
        'selected': SelectedHandler(),
        'disabled': DisabledHandler(),
        'readonly': ReadonlyHandler(),
        'error': ErrorHandler(),
        
        # Routing (3)
        'url': UrlHandler(),
        'active_link': ActiveLinkHandler(),
        'route': RouteHandler(),
        
        # Auth (4)
        'auth': AuthHandler(),
        'guest': GuestHandler(),
        'htmx': HtmxHandler(),
        'non_htmx': NonHtmxHandler(),
        
        # Assets (3)
        'css': CssHandler(),
        'js': JsHandler(),
        'vite': ViteHandler(),
        
        # Data (6)
        'let': LetHandler(),
        'dump': DumpHandler(),
        'span': SpanHandler(),
        'messages': MessagesHandler(),
        'flash': FlashHandler(),
        'status': StatusHandler(),
        
        # Special (2)
        'include': IncludeHandler(),
        'fragment': FragmentHandler(),
        
        # Meta (3)
        'method': MethodHandler(),
        'old': OldHandler(),
        'json': JsonHandler(),
    }


# ================= Module Exports =================

__all__ = [
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
    'create_all_directive_handlers',
]
