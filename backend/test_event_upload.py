import sys
import os
import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from database.db import SessionLocal
    from database.models import User
    from api.routes.events import create_event
    from api.models.schemas import EventCreate
except ImportError:
    from database.db import SessionLocal
    from database.models import User
    from api.routes.events import create_event
    from api.models.schemas import EventCreate

import asyncio
from sqlalchemy.future import select

async def main():
    async with SessionLocal() as db:
        res = await db.execute(select(User))
        user = res.scalars().first()
        if not user:
            user = User(email="test_event@test.local", username="tester")
            db.add(user)
            await db.commit()
            await db.refresh(user)

        print(f"Using direct code call for user {user.id}")

        event_data = EventCreate(
            url="https://github.com/PrageethBanuka",
            domain="github.com",
            title="GitHub Page",
            duration_seconds=45,
            session_id=None,
            timestamp=datetime.datetime.utcnow()
        )

        try:
            result = await create_event(event=event_data, db=db, user=user)
            print("Success! Event created.")
            print(f"Event ID: {result.id}, Domain: {result.domain}, Distraction: {result.is_distraction}")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
