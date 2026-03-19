import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from database.db import SessionLocal
    from database.models import BrowsingEvent, User
except ImportError:
    sys.path.append('.')
    from database.db import SessionLocal
    from database.models import BrowsingEvent, User

db = SessionLocal()
events = db.query(BrowsingEvent).order_by(BrowsingEvent.id.desc()).limit(20).all()
print(f"Total events: {db.query(BrowsingEvent).count()}")
for e in events:
    print(f"Event: {e.id}, User: {e.user_id}, Domain: {e.domain}, Duration: {e.duration_seconds}, TS: {e.timestamp.isoformat() if e.timestamp else None}")
