from eden.middleware import CORSMiddleware
from starlette.applications import Starlette

app = Starlette(routes=[])
middleware = CORSMiddleware(app, allow_origins=['https://example.com'])
print('allowed', middleware.is_allowed_origin('https://example.com'))
print('allowed slash', middleware.is_allowed_origin('https://example.com/'))
print('allowed other', middleware.is_allowed_origin('https://evil.com'))
