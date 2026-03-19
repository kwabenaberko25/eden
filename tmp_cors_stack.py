from eden import Eden
from eden.middleware import CORSMiddleware

app = Eden(debug=True)
app.add_middleware('cors', allow_origins=['https://example.com'])
print('stack before setup_defaults:', [(m[0].__name__ if isinstance(m[0], type) else m[0], m[1], m[2]) for m in app._middleware_stack])
app.setup_defaults()
print('stack after setup_defaults:', [(m[0].__name__ if isinstance(m[0], type) else m[0], m[1], m[2]) for m in app._middleware_stack])

# Also check class and kwargs in existing stack.
for m in app._middleware_stack:
    if isinstance(m[0], type) and m[0].__name__ in ('CORSMiddleware', 'DebugCORS'):
        print('cors entry', m[0], m[1])
