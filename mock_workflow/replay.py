"""
Crude script that replays a captured `with-weblog` event stream to the "executor" web app: allows us to test monitoring
  without rerunning a full workflow
"""
import asyncio

import httpx
import orjson


async def post_record(client, record: object):
    return await client.post("http://127.0.0.1:8000/workflows/insert_id_here/report/", json=record)


async def main():
    with open('weblog-http-stream-insert_id_here.json', 'r') as f:
        records = orjson.loads(f.read())

    async with httpx.AsyncClient() as client:
        for item in records:
            resp = await post_record(client, item)
            print(resp.status_code, resp.json())


asyncio.run(main())
