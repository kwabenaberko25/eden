import asyncio
from eden import Eden
from httpx import ASGITransport, AsyncClient
from eden.middleware import CORSMiddleware as EdenCORSMiddleware

class DebugCORS(EdenCORSMiddleware):
    def is_allowed_origin(self, origin):
        print('DEBUG CORS is_allowed_origin:', origin, 'allow_origins', self.allow_origins)
        return super().is_allowed_origin(origin)

app = Eden(debug=True)
# add this custom middleware directly
app.add_middleware(DebugCORS, allow_origins=['https://example.com'], allow_methods=['GET','POST','OPTIONS'])

@app.get('/data')
async def data():
    return {'data':'hello'}

async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://testserver') as client:
        r = await client.options('/data', headers={'Origin':'https://example.com', 'Access-Control-Request-Method':'GET'})
        print('status', r.status_code)
        print('headers', dict(r.headers))
        print('body', r.text)

asyncio.run(main())
