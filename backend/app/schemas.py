from typing import List, Optional

from pydantic import BaseModel, Field


REPORT_STATUS_LABELS = {
    "draft": "待确认大纲",
    "writing": "写作中",
    "paused": "已暂停",
    "done": "已完成",
}

DOC_STATUS_LABELS = {
    "available": "可用",
    "empty": "无文字",
    "failed": "失败",
}


class DocumentUploadResult(BaseModel):
    filename: str
    ok: bool
    status: str
    status_label: str
    chunk_count: int
    error: Optional[str] = None


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    status_label: str
    chunk_count: int
    size_bytes: int
    error: Optional[str] = None
    created_at: str


class ReportCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    target_words: Optional[int] = 12000
    user_requirements: Optional[str] = ""


class ReportOut(BaseModel):
    id: int
    title: str
    target_words: int
    user_requirements: str
    status: str
    status_label: str
    created_at: str
    updated_at: str


class OutlineChapter(BaseModel):
    chapter_id: int
    title: str
    key_points: List[str] = []
    data_needed: List[str] = []
    suggested_words: int = 0


class OutlineData(BaseModel):
    chapters: List[OutlineChapter] = []
    total_words: int = 0
    chapter_count: int = 0
    needs_manual: bool = False
    message: str = ""


class OutlineUpdate(BaseModel):
    chapters: List[OutlineChapter]


WRITING_STATUS_LABELS = {
    "idle": "未开始",
    "running": "写作中",
    "paused": "已暂停",
    "failed": "失败",
    "done": "已完成",
}


class WritingTaskOut(BaseModel):
    report_id: int
    status: str
    status_label: str
    current_chapter: int
    total_chapters: int
    error: Optional[str] = None
    updated_at: str


class ChapterOut(BaseModel):
    chapter_id: int
    title: str
    body: str
    status: str
    rewrite_count: int
    truncated: bool
    missing: List[str] = []
    retrieved: List[str] = []
    issues: List[dict] = []
    unverifiable: List[str] = []
    summary: str = ""
