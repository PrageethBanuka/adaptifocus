import os
import sys

sys.path.append('.')
from agents.context_agent import ContextAgent
agent = ContextAgent()

titles = [
    "Jujutsu Kaisen ep 5 Full English Sub",
    "Funny cat video compilation 2024",
    "MIT 18.06 Linear Algebra, Spring 2005"
]

for t in titles:
    res = agent.analyze({
        "current_url": "https://www.youtube.com/watch?v=123",
        "current_title": t,
        "current_domain": "youtube.com"
    })
    print(f"\nTitle: '{t}' -> Classification: {res['classification']}, Score: {res['context_score']}, Reasons: {res['reasons']}")
