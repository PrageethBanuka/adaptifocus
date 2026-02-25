"""Load the downloaded Kaggle CSVs into the database and retrain."""
import csv, sys
from datetime import datetime, timedelta
from database.db import init_db, engine
from sqlalchemy import text

sys.stdout.reconfigure(line_buffering=True)
init_db()
conn = engine.connect()

def bulk_insert(rows):
    if not rows:
        return
    vals = ",".join(
        f"('{r[0]}','{r[1]}','{r[2]}','{r[3]}',{r[4]},{r[5]},{r[6]},'{r[7]}')"
        for r in rows
    )
    conn.execute(text(
        "INSERT INTO browsing_events "
        "(timestamp,url,domain,title,duration_seconds,is_distraction,distraction_score,category) "
        f"VALUES {vals}"
    ))
    conn.commit()

# --- Data.csv (Digital Lifestyle Benchmark) ---
print("Loading Data.csv...")
batch, count = [], 0
with open("data/Data.csv") as f:
    for row in csv.DictReader(f):
        sm = float(row.get("social_media_mins", 0))
        st = float(row.get("study_mins", 0))
        ts = datetime.utcnow() - timedelta(days=count % 30, hours=count % 12)
        if st > 0:
            batch.append((ts.replace(hour=9).isoformat(), "https://kaggle.example.com/study",
                "docs.python.org", "Study (Kaggle)", int(st*60), 0, 0.1, "study"))
        if sm > 0:
            batch.append((ts.replace(hour=15).isoformat(), "https://kaggle.example.com/social",
                "youtube.com", "Social Media (Kaggle)", int(sm*60), 1, 0.8, "distraction"))
        count += 1
        if len(batch) >= 500:
            bulk_insert(batch); batch = []
bulk_insert(batch)
print(f"  {count} rows processed from Data.csv")

# --- Student Digital Habits ---
print("Loading Student_Digital_Habits.csv...")
batch, count2 = [], 0
with open("data/Student_Digital_Habits_and_Academic_Wellbeing.csv") as f:
    for row in csv.DictReader(f):
        scr = float(row.get("daily_screen_time_hours", 0))
        sm = float(row.get("social_media_hours", 0))
        st = max(0, scr - sm)
        ts = datetime.utcnow() - timedelta(days=count2 % 30, hours=count2 % 8)
        if st > 0:
            batch.append((ts.replace(hour=10).isoformat(), "https://kaggle.example.com/student",
                "github.com", "Student Study (Kaggle)", int(st*3600), 0, 0.1, "study"))
        if sm > 0:
            batch.append((ts.replace(hour=16).isoformat(), "https://kaggle.example.com/sm",
                "instagram.com", "Student Social (Kaggle)", int(sm*3600), 1, 0.85, "distraction"))
        count2 += 1
bulk_insert(batch)
print(f"  {count2} rows processed from Student_Digital_Habits.csv")

total = conn.execute(text("SELECT COUNT(*) FROM browsing_events")).fetchone()[0]
print(f"\nTotal events in DB: {total}")
conn.close()
print("Done! Now run: python -m ml.train_pipeline")
