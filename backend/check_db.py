import sys
import datetime
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
users = db.query(User).all()
print(f"Total Users: {len(users)}")
for u in users:
    print(f"User {u.id} - email: {u.email}")
today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
events = db.query(BrowsingEvent).filter(BrowsingEvent.timestamp >= today_start).order_by(BrowsingEvent.timestamp.desc()).limit(10).all()
print(f"Total Events Today: {db.query(BrowsingEvent).filter(BrowsingEvent.timestamp >= today_start).count()}")
for e in events:
    print(f"Event: {e.id}, User: {e.user_id}, Domain: {e.domain}, Duration: {e.duration_seconds}, Distraction: {e.is_distraction}, Timestamp: {e.timestamp}")
