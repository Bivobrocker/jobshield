
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func

from backend.database.db import Base


class JobAnalysis(Base):
    __tablename__ = "job_analyses"

    analysis_id = Column(String(50), primary_key=True, index=True)
    verdict = Column(String(50), nullable=False)

    company_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)

    job_text = Column(Text, nullable=False)

    vacancy_verification = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
