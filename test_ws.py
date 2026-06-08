import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8000/ws/query") as ws:
        await ws.send(json.dumps({"question": "How many orders were delivered successfully?"}))
        
        async for message in ws:
            chunk = json.loads(message)
            print(json.dumps(chunk, indent=2))

asyncio.run(test())