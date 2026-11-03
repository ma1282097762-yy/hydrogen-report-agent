import json

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from . import models, schemas
from .config import settings
from .db import get_db
from .errors import ApiError
from .schemas import WRITING_STATUS_LABELS
from .services import outline as outline_service
from .services import repository
from .services import writer

router = APIRouter(prefix="/api/v1")


@router.post("/documents")
def upload_documents(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    if not files:
        raise ApiError("NO_FILES", "未选择文件")
    return {"documents": [repository.upload_document(db, f) for f in files]}


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    return {"documents": [repository.document_out(d) for d in repository.list_documents(db)]}


@router.post("/reports")
def create_report(payload: schemas.ReportCreate, db: Session = Depends(get_db)):
    target = payload.target_words if payload.target_words is not None else settings.default_target_words
    if target < 1 or target > settings.max_target_words:
        raise ApiError("INVALID_TARGET_WORDS", f"目标字数必须在 1 到 {settings.max_target_words} 之间")
    r = models.Report(
        owner_id="default",
        title=payload.title.strip(),
        target_words=target,
        user_requirements=payload.user_requirements or "",
        status="draft",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return repository.report_out(r)


@router.get("/reports")
def list_reports(db: Session = Depends(get_db)):
    return {"reports": [repository.report_out(r) for r in repository.list_reports(db)]}


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    r = db.get(models.Report, report_id)
    if not r:
        raise ApiError("NOT_FOUND", "报告不存在", 404)
    return repository.report_out(r)


@router.post("/reports/{report_id}/outline/generate")
def generate_outline(report_id: int, db: Session = Depends(get_db)):
    r = db.get(models.Report, report_id)
    if not r:
        raise ApiError("NOT_FOUND", "报告不存在", 404)
    data, result = outline_service.generate_outline(r)
    repository.save_outline(db, r, data)
    return {
        "outline": data.model_dump(),
        "model": {"tokens_in": result.tokens_in, "tokens_out": result.tokens_out,
                  "duration_s": result.duration_s, "request_id": result.request_id},
    }


@router.get("/reports/{report_id}/outline")
def get_outline(report_id: int, db: Session = Depends(get_db)):
    o = db.query(models.Outline).filter(models.Outline.report_id == report_id).first()
    if not o:
        raise ApiError("NOT_FOUND", "大纲不存在，请先生成", 404)
    return repository.outline_out(o)


@router.put("/reports/{report_id}/outline")
def update_outline(report_id: int, payload: schemas.OutlineUpdate, db: Session = Depends(get_db)):
    r = db.get(models.Report, report_id)
    if not r:
        raise ApiError("NOT_FOUND", "报告不存在", 404)
    data = outline_service.normalize_chapters(payload.chapters, r.target_words, allow_scale=False)
    repository.save_outline(db, r, data)
    return {"outline": data.model_dump()}


@router.post("/reports/{report_id}/outline/confirm")
def confirm_outline(report_id: int, db: Session = Depends(get_db)):
    r = db.get(models.Report, report_id)
    if not r:
        raise ApiError("NOT_FOUND", "报告不存在", 404)
    o = db.query(models.Outline).filter(models.Outline.report_id == report_id).first()
    if not o:
        raise ApiError("NO_OUTLINE", "请先生成大纲", 400)
    data = repository.outline_to_data(o)
    if data.chapter_count < 1:
        raise ApiError("EMPTY_OUTLINE", "大纲为空", 400)
    if data.total_words > settings.max_target_words:
        raise ApiError("TOO_LONG", f"字数合计超过 {settings.max_target_words}，请调整", 400)
    r.status = "writing"
    db.commit()
    db.refresh(r)
    return {"report": repository.report_out(r)}


def _task_out(task):
    return {
        "report_id": task.report_id,
        "status": task.status,
        "status_label": WRITING_STATUS_LABELS.get(task.status, task.status),
        "current_chapter": task.current_chapter,
        "total_chapters": task.total_chapters,
        "error": task.error,
        "updated_at": task.updated_at.strftime("%Y-%m-%d %H:%M:%S") if task.updated_at else "",
    }


def _chapter_out(c):
    audit = json.loads(c.audit_json) if c.audit_json else {}
    return {
        "chapter_id": c.chapter_id, "title": c.title, "body": c.body,
        "status": c.status, "rewrite_count": c.rewrite_count,
        "truncated": bool(c.truncated),
        "missing": json.loads(c.missing_json) if c.missing_json else [],
        "retrieved": json.loads(c.retrieved_json) if c.retrieved_json else [],
        "issues": (audit or {}).get("issues") or [],
        "unverifiable": (audit or {}).get("unverifiable") or [],
        "summary": c.summary,
    }


@router.post("/reports/{report_id}/write")
def start_write(report_id: int, db: Session = Depends(get_db)):
    report = db.get(models.Report, report_id)
    if not report:
        raise ApiError("NOT_FOUND", "报告不存在", 404)
    if report.status != "writing":
        raise ApiError("NOT_CONFIRMED", "请先确认大纲", 400)
    task = writer.get_or_create_task(db, report)
    if task.status == "running":
        raise ApiError("ALREADY_RUNNING", "已在写作中", 409)
    task.status = "running"
    task.pause_requested = 0
    task.error = None
    db.commit()
    writer.spawn(report_id)
    db.refresh(task)
    return {"task": _task_out(task)}


@router.get("/reports/{report_id}/write")
def get_write(report_id: int, db: Session = Depends(get_db)):
    if not db.get(models.Report, report_id):
        raise ApiError("NOT_FOUND", "报告不存在", 404)
    task = db.query(models.WritingTask).filter(models.WritingTask.report_id == report_id).first()
    chapters = (db.query(models.ChapterRecord)
                .filter(models.ChapterRecord.report_id == report_id)
                .order_by(models.ChapterRecord.chapter_id).all())
    return {"task": _task_out(task) if task else None,
            "chapters": [_chapter_out(c) for c in chapters]}


@router.post("/reports/{report_id}/write/resume")
def resume_write(report_id: int, db: Session = Depends(get_db)):
    report = db.get(models.Report, report_id)
    if not report:
        raise ApiError("NOT_FOUND", "报告不存在", 404)
    task = writer.get_or_create_task(db, report)
    if task.status == "running":
        raise ApiError("ALREADY_RUNNING", "已在写作中", 409)
    task.status = "running"
    task.pause_requested = 0
    task.error = None
    report.status = "writing"
    db.commit()
    writer.spawn(report_id)
    db.refresh(task)
    return {"task": _task_out(task)}


@router.post("/reports/{report_id}/write/pause")
def pause_write(report_id: int, db: Session = Depends(get_db)):
    task = writer.request_pause(db, report_id)
    return {"task": _task_out(task)}


@router.get("/reports/{report_id}/chapters")
def list_chapters(report_id: int, db: Session = Depends(get_db)):
    if not db.get(models.Report, report_id):
        raise ApiError("NOT_FOUND", "报告不存在", 404)
    chapters = (db.query(models.ChapterRecord)
                .filter(models.ChapterRecord.report_id == report_id)
                .order_by(models.ChapterRecord.chapter_id).all())
    return {"chapters": [_chapter_out(c) for c in chapters]}
