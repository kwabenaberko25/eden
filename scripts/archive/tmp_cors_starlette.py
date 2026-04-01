import asyncio
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient

app = Starlette(debug=True, routes=[ ])

@app.route('/data', methods=['GET'])
async def data(request):
    return JSONResponse({'data':'hello'})

app.add_middleware(CORSMiddleware, allow_origins=['https://example.com'], allow_methods=['GET','POST','OPTIONS'])

async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://testserver') as client:
        r = await client.options('/data', headers={'Origin':'https://example.com', 'Access-Control-Request-Method':'GET'})
        print('status', r.status_code)
        print('headers', dict(r.headers))
        print('body', r.text)

asyncio.run(main())
