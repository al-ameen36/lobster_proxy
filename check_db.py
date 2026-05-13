import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.interaction import Interaction

async def check_db():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Interaction))
        interactions = result.scalars().all()
        print(f"Total interactions logged: {len(interactions)}")
        for i in interactions:
            print(f"[{i.timestamp}] ID: {i.request_id} | Verdict: {i.verdict} | Model: {i.model}")
            print(f"  User: {i.user_message[:50]}...")
            print(f"  Response: {i.final_response[:50]}...")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(check_db())
