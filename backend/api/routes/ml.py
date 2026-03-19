"""Machine Learning routes for evaluation and continuous learning."""

from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.db import get_db
from database.models import User, UserFeedback
from api.auth import require_user

router = APIRouter(prefix="/ml", tags=["machine_learning"])

class FeedbackRequest(BaseModel):
    url: str
    domain: str
    prediction: str
    actual_category: str
    is_false_positive: bool = True

@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """
    Submit feedback on an ML classification.
    Used for continuous learning when the model flags a productive site as a distraction.
    """
    feedback = UserFeedback(
        user_id=user.id,
        url=request.url,
        domain=request.domain,
        prediction=request.prediction,
        actual_category=request.actual_category,
        is_false_positive=request.is_false_positive,
        timestamp=datetime.utcnow()
    )
    db.add(feedback)
    await db.commit()
    
    return {"status": "ok", "message": "Feedback recorded for future model training."}
