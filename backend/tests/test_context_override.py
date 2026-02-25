"""Test the context-aware classification — verifies YouTube override works."""
from agents.context_agent import ContextAgent

agent = ContextAgent()

tests = [
    {
        "name": "YouTube cat video → DISTRACTION",
        "data": {"current_domain": "youtube.com", "current_title": "Funny Cat Compilation 2024"},
        "expect": "distraction",
    },
    {
        "name": "YouTube MIT lecture → STUDY",
        "data": {"current_domain": "youtube.com", "current_title": "MIT 6.006 Data Structures Algorithm Lecture 1"},
        "expect": "study",
    },
    {
        "name": "YouTube ML tutorial + topic → STUDY",
        "data": {"current_domain": "youtube.com", "current_title": "Python Machine Learning Tutorial", "study_topic": "machine learning"},
        "expect": "study",
    },
    {
        "name": "YouTube homepage → DISTRACTION",
        "data": {"current_domain": "youtube.com", "current_title": "YouTube"},
        "expect": "distraction",
    },
    {
        "name": "Google Scholar → STUDY",
        "data": {"current_domain": "scholar.google.com", "current_title": "Research papers"},
        "expect": "study",
    },
    {
        "name": "Instagram → DISTRACTION",
        "data": {"current_domain": "instagram.com", "current_title": "Instagram"},
        "expect": "distraction",
    },
    {
        "name": "Reddit + Python programming → STUDY or NEUTRAL",
        "data": {"current_domain": "reddit.com", "current_title": "Understanding Python programming async await tutorial"},
        "expect_not": "distraction",
    },
]

passed, failed = 0, 0
for t in tests:
    r = agent.analyze(t["data"])
    cls = r["classification"]
    score = r["context_score"]

    if "expect" in t:
        ok = cls == t["expect"]
    else:
        ok = cls != t["expect_not"]

    status = "✅ PASS" if ok else "❌ FAIL"
    if not ok: failed += 1
    else: passed += 1

    print(f"{status} {t['name']}")
    print(f"       Got: {cls} (score: {score})")
    for reason in r["reasons"]:
        print(f"       - {reason}")
    print()

print(f"\nResults: {passed}/{passed+failed} passed")
