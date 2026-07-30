from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base


class Subject(Base):
    """Reference table for subjects (reading, math, science, etc.)."""
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g. "math", "reading"
    title = Column(String(255), nullable=False)  # human-readable name
    title_kz = Column(String(255), nullable=True)  # Kazakh translation
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<Subject {self.code}: {self.title}>"
