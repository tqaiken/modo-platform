"""Service for writing immutable audit logs."""
from sqlalchemy.orm import Session
from app.models.log import QuestionLog, LogAction


def log_action(
    db: Session,
    question_id: int,
    user_id: int,
    action: LogAction,
    details: str | None = None,
) -> QuestionLog:
    """Create an immutable log entry for a question action."""
    entry = QuestionLog(
        question_id=question_id,
        user_id=user_id,
        action=action,
        details=details,
    )
    db.add(entry)
    db.flush()  # get ID without committing
    return entry
