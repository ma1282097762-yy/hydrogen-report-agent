import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import settings
from .. import models
from ..schemas import DOC_STATUS_LABELS, REPORT_STATUS_LABELS, OutlineData
from . import parsing


def _iso(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def upload_document(db: Session, uploadfile) -> dict:
    filename = uploadfile.filename or "unnamed"
    ext = Path(filename).suffix.lower()
    settings.ensure_dirs()

    if ext not in parsing.ALLOWED_EXTS:
        return {"filename": filename, "ok": False, "status": "failed",
                "status_label": "失败", "chunk_count": 0,
                "error": "当前格式不支持，请上传 PDF、Word、Markdown 或 TXT"}

    stored = settings.uploads_dir / parsing.safe_store_name(ext)
    size = 0
    try:
        with open(stored, "wb") as out:
            while True:
                buf = uploadfile.file.read(1024 * 1024)
                if not buf:
                    break
                size += len(buf)
                if size > settings.upload_max_bytes:
                    out.close()
                    stored.unlink(missing_ok=True)
                    return {"filename": filename, "ok": False, "status": "failed",
                            "status_label": "失败", "chunk_count": 0,
                            "error": "上传失败，最大支持 100M 文件"}
                out.write(buf)
    except Exception as e:  # noqa
        stored.unlink(missing_ok=True)
        return {"filename": filename, "ok": False, "status": "failed",
                "status_label": "失败", "chunk_count": 0,
                "error": f"上传失败：{type(e).__name__}"}

    text, err = parsing.extract_text(stored, ext)
    if err:
        stored.unlink(missing_ok=True)
        return {"filename": filename, "ok": False, "status": "failed",
                "status_label": "失败", "chunk_count": 0, "error": err}

    doc = models.Document(
        owner_id="default", filename=filename, stored_path=str(stored),
        file_type=ext.lstrip("."), size_bytes=size,
    )
    if not text.strip():
        doc.status = "empty"
        doc.error = "无文字，检索不到"
        db.add(doc)
        db.commit()
        return {"filename": filename, "ok": True, "status": "empty",
                "status_label": "无文字", "chunk_count": 0, "error": "无文字，检索不到"}

    chunks = parsing.chunk_text(text)
    doc.status = "available"
    doc.chunk_count = len(chunks)
    db.add(doc)
    db.flush()
    for i, c in enumerate(chunks):
        db.add(models.Chunk(document_id=doc.id, chunk_index=i, text=c,
                           char_count=parsing.char_count(c)))
    db.commit()
    return {"filename": filename, "ok": True, "status": "available",
            "status_label": "可用", "chunk_count": len(chunks), "error": None}


def list_documents(db: Session):
    return db.query(models.Document).order_by(models.Document.created_at.desc()).all()


def document_out(d) -> dict:
    return {
        "id": d.id, "filename": d.filename, "file_type": d.file_type,
        "status": d.status, "status_label": DOC_STATUS_LABELS.get(d.status, d.status),
        "chunk_count": d.chunk_count, "size_bytes": d.size_bytes, "error": d.error,
        "created_at": _iso(d.created_at),
    }


def list_reports(db: Session):
    return db.query(models.Report).order_by(models.Report.created_at.desc()).all()


def report_out(r) -> dict:
    return {
        "id": r.id, "title": r.title, "target_words": r.target_words,
        "user_requirements": r.user_requirements or "",
        "status": r.status, "status_label": REPORT_STATUS_LABELS.get(r.status, r.status),
        "created_at": _iso(r.created_at), "updated_at": _iso(r.updated_at),
    }


def save_outline(db: Session, report, data: OutlineData):
    existing = db.query(models.Outline).filter(models.Outline.report_id == report.id).first()
    chapters_json = json.dumps([c.model_dump() for c in data.chapters], ensure_ascii=False)
    if existing:
        existing.chapters_json = chapters_json
        existing.total_words = data.total_words
        existing.chapter_count = data.chapter_count
        existing.updated_at = datetime.utcnow()
    else:
        db.add(models.Outline(report_id=report.id, chapters_json=chapters_json,
                              total_words=data.total_words, chapter_count=data.chapter_count))
    db.commit()


def outline_out(o) -> dict:
    try:
        chapters = json.loads(o.chapters_json)
    except json.JSONDecodeError:
        chapters = []
    return {
        "report_id": o.report_id, "chapters": chapters,
        "total_words": o.total_words, "chapter_count": o.chapter_count,
        "updated_at": _iso(o.updated_at),
    }


def outline_to_data(o) -> OutlineData:
    try:
        chapters = json.loads(o.chapters_json)
    except json.JSONDecodeError:
        chapters = []
    data = OutlineData(chapters=chapters, total_words=o.total_words, chapter_count=o.chapter_count)
    return data
