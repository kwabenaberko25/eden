from eden.templating.parser import TemplateSyntaxError
from jinja2.exceptions import TemplateError as JinjaTemplateError

exc = TemplateSyntaxError("Unclosed block", line=10, column=5)
print(f"str(exc): {str(exc)}")
print(f"getattr(exc, 'message', None): {getattr(exc, 'message', None)}")
print(f"isinstance(exc, JinjaTemplateError): {isinstance(exc, JinjaTemplateError)}")
print(f"exc.lineno: {getattr(exc, 'lineno', None)}")
print(f"exc.column: {getattr(exc, 'column', None)}")
