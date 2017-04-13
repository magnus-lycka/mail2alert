import asyncio
import aioredis

loop = asyncio.get_event_loop()

async def go():
    redis = await aioredis.create_redis(
        ('localhost', 6379), loop=loop)
    await redis.set('my-key', 'value')
    val = await redis.get('my-key')
    print(val)
    redis.close()
    await redis.wait_closed()
loop.run_until_complete(go())
