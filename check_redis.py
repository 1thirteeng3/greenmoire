import os, asyncio
from redis.asyncio import Redis

async def main():
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    r = Redis.from_url(redis_url)
    try:
        info = await r.xinfo_stream('stream:user_input')
        print('Stream info:', info)
    except Exception as e:
        print('Error getting stream info:', e)
    try:
        groups = await r.xinfo_groups('stream:user_input')
        print('Groups:', groups)
    except Exception as e:
        print('Error getting groups:', e)
    await r.close()

if __name__ == '__main__':
    asyncio.run(main())
