from datetime import datetime
from sqlalchemy import String, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    model: Mapped[str] = mapped_column(String(100))
    user_message: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(String(50))
    policy_reason: Mapped[str] = mapped_column(Text, nullable=True)
    final_response: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Interaction(id={self.id}, request_id={self.request_id}, verdict={self.verdict})>"
