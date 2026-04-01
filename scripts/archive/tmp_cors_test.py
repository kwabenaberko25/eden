import asyncio
from eden import Eden
from httpx import ASGITransport, AsyncClient

app = Eden(debug=True)
app.add_middleware('cors', allow_origins=['https://example.com'])

@app.get('/data')
async def data():
    return {'data': 'hello'}

async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://testserver') as client:
        r = await client.options('/data', headers={'Origin':'https://example.com', 'Access-Control-Request-Method':'GET'})
        print('status', r.status_code)
        print('headers', dict(r.headers))
        print('body', r.text)

asyncio.run(main())
