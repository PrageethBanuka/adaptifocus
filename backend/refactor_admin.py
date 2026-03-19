import re

def main():
    with open("api/routes/admin.py", "r") as f:
        content = f.read()

    # Imports
    content = content.replace("from sqlalchemy.orm import Session", "from sqlalchemy.ext.asyncio import AsyncSession\nfrom sqlalchemy.future import select")
    content = content.replace("db: Session = Depends(get_db)", "db: AsyncSession = Depends(get_db)")

    # Async defs
    content = content.replace("def admin_overview(", "async def admin_overview(")
    content = content.replace("def admin_users(", "async def admin_users(")
    content = content.replace("def experiment_comparison(", "async def experiment_comparison(")
    content = content.replace("def top_domains(", "async def top_domains(")

    # Replacements for `count()`
    content = re.sub(r'total_users = db\.query\(User\)\.count\(\)', r'res = await db.execute(select(func.count(User.id)))\n    total_users = res.scalar()', content)
    content = re.sub(r'total_events = db\.query\(BrowsingEvent\)\.count\(\)', r'res = await db.execute(select(func.count(BrowsingEvent.id)))\n    total_events = res.scalar()', content)
    content = re.sub(r'total_sessions = db\.query\(StudySession\)\.count\(\)', r'res = await db.execute(select(func.count(StudySession.id)))\n    total_sessions = res.scalar()', content)
    content = re.sub(r'total_interventions = db\.query\(Intervention\)\.count\(\)', r'res = await db.execute(select(func.count(Intervention.id)))\n    total_interventions = res.scalar()', content)

    # General pattern roughly .scalar()
    # active_users
    content = re.sub(r'active_users = \(\n\s*db\.query\((.*?)\)\n\s*\.filter\((.*?)\)\n\s*\.scalar\(\)\n\s*\)', r'res = await db.execute(select(\1).filter(\2))\n    active_users = res.scalar() or 0', content)

    # groups
    content = re.sub(r'groups = \(\n\s*db\.query\((.*?)\)\n\s*\.group_by\((.*?)\)\n\s*\.all\(\)\n\s*\)', r'res = await db.execute(select(\1).group_by(\2))\n    groups = res.all()', content)

    # single line scalars like total_seconds
    content = re.sub(r'total_seconds = db\.query\((.*?)\)\.scalar\(\) or 0', r'res = await db.execute(select(\1))\n    total_seconds = res.scalar() or 0', content)
    content = re.sub(r'distraction_seconds = \(\n\s*db\.query\((.*?)\)\n\s*\.filter\((.*?)\)\n\s*\.scalar\(\) or 0\n\s*\)', r'res = await db.execute(select(\1).filter(\2))\n    distraction_seconds = res.scalar() or 0', content)

    # Users loop
    content = re.sub(r'users = db\.query\(User\)\.order_by\(User\.created_at\.desc\(\)\)\.all\(\)', r'res = await db.execute(select(User).order_by(User.created_at.desc()))\n    users = res.scalars().all()', content)
    content = re.sub(r'event_count = db\.query\(BrowsingEvent\)\.filter\(\n\s*BrowsingEvent\.user_id == user\.id\n\s*\)\.count\(\)', r'res = await db.execute(select(func.count(BrowsingEvent.id)).filter(BrowsingEvent.user_id == user.id))\n        event_count = res.scalar() or 0', content)
    content = re.sub(r'total_sec = \(\n\s*db\.query\((.*?)\)\n\s*\.filter\((.*?)\)\n\s*\.scalar\(\) or 0\n\s*\)', r'res = await db.execute(select(\1).filter(\2))\n        total_sec = res.scalar() or 0', content)
    content = re.sub(r'session_count = db\.query\(StudySession\)\.filter\(\n\s*StudySession\.user_id == user\.id\n\s*\)\.count\(\)', r'res = await db.execute(select(func.count(StudySession.id)).filter(StudySession.user_id == user.id))\n        session_count = res.scalar() or 0', content)
    content = re.sub(r'intervention_count = db\.query\(Intervention\)\.filter\(\n\s*Intervention\.user_id == user\.id\n\s*\)\.count\(\)', r'res = await db.execute(select(func.count(Intervention.id)).filter(Intervention.user_id == user.id))\n        intervention_count = res.scalar() or 0', content)
    content = re.sub(r'last_event = \(\n\s*db\.query\((.*?)\)\n\s*\.filter\((.*?)\)\n\s*\.order_by\((.*?)\)\n\s*\.first\(\)\n\s*\)', r'res = await db.execute(select(\1).filter(\2).order_by(\3))\n        last_event = res.scalars().first()', content)


    # Experiment comparison
    content = re.sub(r'group_users = db\.query\(User\)\.filter\(User\.experiment_group == group\)\.all\(\)', r'res = await db.execute(select(User).filter(User.experiment_group == group))\n        group_users = res.scalars().all()', content)
    
    # distraction_sec override inside experiment_comparison
    # Replace all .count()
    content = re.sub(r'session_count = \(\n\s*db\.query\(StudySession\)\n\s*\.filter\(StudySession\.user_id\.in_\(user_ids\)\)\n\s*\.count\(\)\n\s*\)', r'res = await db.execute(select(func.count(StudySession.id)).filter(StudySession.user_id.in_(user_ids)))\n        session_count = res.scalar() or 0', content)
    content = re.sub(r'intervention_count = \(\n\s*db\.query\(Intervention\)\n\s*\.filter\(Intervention\.user_id\.in_\(user_ids\)\)\n\s*\.count\(\)\n\s*\)', r'res = await db.execute(select(func.count(Intervention.id)).filter(Intervention.user_id.in_(user_ids)))\n        intervention_count = res.scalar() or 0', content)


    # Top Domains
    content = re.sub(r'domains = \(\n\s*db\.query\(\n\s*(.*?)\n\s*\)\n\s*\.filter\((.*?)\)\n\s*\.group_by\((.*?)\)\n\s*\.order_by\((.*?)\)\n\s*\.limit\(limit\)\n\s*\.all\(\)\n\s*\)', r'res = await db.execute(select(\1).filter(\2).group_by(\3).order_by(\4).limit(limit))\n    domains = res.all()', content)

    # Some remaining specific cases
    content = content.replace("distraction_sec = (", "res = await db.execute(select(func.sum(BrowsingEvent.duration_seconds)).filter(BrowsingEvent.user_id == user.id, BrowsingEvent.is_distraction == True))\n        distraction_sec = res.scalar() or 0\n        # (")

    with open("api/routes/admin.py", "w") as f:
        f.write(content)

if __name__ == "__main__":
    main()
