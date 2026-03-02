import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal
from models import Form_data, AuthUser

async def test():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AuthUser).limit(1))
        user = result.scalars().first()
        print(f"User: {user.username if user else 'None'}")
        
asyncio.run(test())
