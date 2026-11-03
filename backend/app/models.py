from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .db import Base


def now():
    return datetime.utcnow()


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    owner_id = Column(String(64), nullable=False, default="default")
    filename = Column(String(512), nullable=False)
    stored_path = Column(String(1024), nullable=False)
    file_type = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False, default="available")  # available / empty / failed
    chunk_count = Column(Integer, nullable=False, default=0)
    size_bytes = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=now)

    chunks = relationship("Chunk", backref="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    char_count = Column(Integer, nullable=False, default=0)


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    owner_id = Column(String(64), nullable=False, default="default")
    title = Column(String(512), nullable=False)
    target_words = Column(Integer, nullable=False, default=12000)
    user_requirements = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="draft")  # draft / writing / paused / done
    created_at = Column(DateTime, nullable=False, default=now)
    updated_at = Column(DateTime, nullable=False, default=now, onupdate=now)


class Outline(Base):
    __tablename__ = "outlines"
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, unique=True)
    chapters_json = Column(Text, nullable=False, default="[]")
    total_words = Column(Integer, nullable=False, default=0)
    chapter_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=now)
    updated_at = Column(DateTime, nullable=False, default=now, onupdate=now)


class TruthBase(Base):
    __tablename__ = "truth_bases"
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, unique=True)
    data_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, default=now)


class ChapterRecord(Base):
    __tablename__ = "chapters"
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    chapter_id = Column(Integer, nullable=False)
    title = Column(String(512), nullable=False)
    body = Column(Text, nullable=False, default="")
    original_body = Column(Text, nullable=False, default="")
    status = Column(String(16), nullable=False, default="通过")  # 通过 / 待人工 / 失败
    audit_json = Column(Text, nullable=True)
    rewrite_count = Column(Integer, nullable=False, default=0)
    truncated = Column(Integer, nullable=False, default=0)  # 0 / 1
    retrieved_json = Column(Text, nullable=True)  # 文件名列表
    missing_json = Column(Text, nullable=True)
    summary = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=now)
    updated_at = Column(DateTime, nullable=False, default=now, onupdate=now)


class WritingTask(Base):
    __tablename__ = "writing_tasks"
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, unique=True)
    status = Column(String(16), nullable=False, default="idle")  # idle / running / paused / failed / done
    current_chapter = Column(Integer, nullable=False, default=0)
    total_chapters = Column(Integer, nullable=False, default=0)
    pause_requested = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=now, onupdate=now)
