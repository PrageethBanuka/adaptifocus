import sys
sys.path.append('.')
from agents.context_agent import ContextAgent

agent = ContextAgent()

titles = [
    "Chinese Remainder Theorem Introduction",
    "Discrete Mathematics: Chinese Remainder Theorem",
    "Number Theory - Chinese Remainder Theorem"
]

for t in titles:
    res = agent.analyze({
        "current_url": "https://www.youtube.com/watch?v=123",
        "current_title": t,
        "current_domain": "youtube.com"
    })
    print(f"\nTitle: '{t}' -> Classification: {res['classification']}, Score: {res['context_score']}, Reasons: {res['reasons']}")
