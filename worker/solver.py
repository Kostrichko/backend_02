import asyncio


async def work(payload: str) -> str:
    await asyncio.sleep(5)
    return f"{payload} - processed"
