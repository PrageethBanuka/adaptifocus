import sys
import os
from datetime import datetime, timezone

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

        # Create a timezone AWARE datetime (which the extension sends using new Date().toISOString())
        tz_aware_dt = datetime.now(timezone.utc)

        event_data = EventCreate(
            url="https://github.com/PrageethBanuka/test_tz",
            domain="github.com",
            title="Timezone Test",
            duration_seconds=15,
            session_id=None,
            timestamp=tz_aware_dt
        )

        try:
            result = await create_event(event=event_data, db=db, user=user)
            print("Success! Timezone-aware date saved.")
        except Exception as e:
            print(f"Failed timezone-aware save: {e}")

if __name__ == "__main__":
    asyncio.run(main())
