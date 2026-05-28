import json
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ResponseHistoryRecord(Base):
    __tablename__ = "response_history"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_path: Mapped[str] = mapped_column(Text, nullable=False)
    request_name: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    elapsed_ms: Mapped[float] = mapped_column(Float, nullable=False)
    request_headers: Mapped[str] = mapped_column(Text, nullable=False)
    request_body: Mapped[str] = mapped_column(Text, nullable=False)
    response_headers: Mapped[str] = mapped_column(Text, nullable=False)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
    encoding: Mapped[str] = mapped_column(String(64), nullable=False)
    warnings: Mapped[str] = mapped_column(Text, nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "sent_at": self.sent_at.isoformat(),
            "request_path": self.request_path,
            "request_name": self.request_name,
            "environment": self.environment,
            "method": self.method,
            "url": self.url,
            "status_code": self.status_code,
            "elapsed_ms": self.elapsed_ms,
            "request_headers": json.loads(self.request_headers),
            "request_body": self.request_body,
            "response_headers": json.loads(self.response_headers),
            "response_body": self.response_body,
            "encoding": self.encoding,
            "warnings": json.loads(self.warnings),
        }


class CookieRecord(Base):
    __tablename__ = "cookies"

    hostname: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
