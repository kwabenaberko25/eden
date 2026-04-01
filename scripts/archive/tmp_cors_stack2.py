from eden import Eden

app = Eden(debug=True)
print('stack on init', [(m[0].__name__ if isinstance(m[0], type) else m[0], m[1], m[2]) for m in app._middleware_stack])
app.add_middleware('cors', allow_origins=['https://example.com'])
print('stack after add', [(m[0].__name__ if isinstance(m[0], type) else m[0], m[1], m[2]) for m in app._middleware_stack])

app2 = Eden(debug=True)
# if we add subclass in user stack and verify has_cors detection on second call (should no add) and check we maybe not call directly
