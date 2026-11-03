import json
import threading
from datetime import datetime

from sqlalchemy.orm import Session

from .. import db as dbm
from .. import models
from ..errors import ApiError
from ..prompts import (AUDIT_PROMPT, COMPRESS_ADDON, EXTRACT_PROMPT,
                       REWRITE_ADDON, TRUTH_FIELDS, TRUTH_FIELDS_TEXT, WRITE_PROMPT)
from . import llm, retriever
from .parsing import char_count

_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(report_id):
    with _LOCKS_GUARD:
        if report_id not in _LOCKS:
            _LOCKS[report_id] = threading.Lock()
        return _LOCKS[report_id]


def _new_session() -> Session:
    if dbm.SessionLocal is None:
        dbm.init_db()
    return dbm.SessionLocal()


def get_or_create_task(db: Session, report) -> models.WritingTask:
    task = db.query(models.WritingTask).filter(models.WritingTask.report_id == report.id).first()
    if not task:
        task = models.WritingTask(report_id=report.id, status="idle")
        db.add(task)
        db.commit()
        db.refresh(task)
    return task


def _validated_data_text(vd):
    parts = [f"{k}：{v}" for k, v in (vd or {}).items() if v]
    return "\n".join(parts) if parts else "（空）"


def _terminology_text(t):
    return "\n".join(t or []) or "（无）"


def _validate_truth_base(raw) -> dict:
    vd = raw.get("validated_data") or {}
    sources = raw.get("sources") or {}
    terminology = raw.get("global_terminology") or []
    out_vd, out_sources = {}, {}
    for name, _desc in TRUTH_FIELDS:
        val = vd.get(name)
        out_vd[name] = val if isinstance(val, str) and val.strip() else None
        if out_vd[name]:
            src = sources.get(name)
            out_sources[name] = src if isinstance(src, str) and src.strip() else "未标注"
    out_term = [str(x) for x in terminology if isinstance(x, str) and x.strip()][:10]
    return {"validated_data": out_vd, "sources": out_sources, "global_terminology": out_term}


def extract_truth_base(db: Session, report) -> dict:
    context_parts, seen = [], set()
    for _name, desc in TRUTH_FIELDS:
        for item in retriever.retrieve(db, desc, k=3):
            if item["text"] in seen:
                continue
            seen.add(item["text"])
            context_parts.append(f"【来源：{item['filename']}】\n{item['text']}")
    context = "\n\n".join(context_parts) or "（资料库为空）"
    prompt = EXTRACT_PROMPT.format(title=report.title, fields=TRUTH_FIELDS_TEXT, context=context)
    result = llm.call_json(prompt)
    validated = _validate_truth_base(result.data or {})
    row = db.query(models.TruthBase).filter(models.TruthBase.report_id == report.id).first()
    data_json = json.dumps(validated, ensure_ascii=False)
    if row:
        row.data_json = data_json
    else:
        db.add(models.TruthBase(report_id=report.id, data_json=data_json))
    db.commit()
    return validated


def load_truth_base(db: Session, report) -> dict:
    row = db.query(models.TruthBase).filter(models.TruthBase.report_id == report.id).first()
    if not row:
        return extract_truth_base(db, report)
    return json.loads(row.data_json)


def _last_sentence(body):
    b = (body or "").strip()
    if not b:
        return ""
    seps = ("。", "！", "？", ".", "!", "?")
    last = max([b.rfind(s) for s in seps])
    if last == -1:
        return b
    prev = -1
    for s in seps:
        p = b.rfind(s, 0, last)
        prev = max(prev, p)
    return b[prev + 1:last + 1].strip()


def _critical_count(audit):
    try:
        return int((audit or {}).get("critical_count") or 0)
    except (ValueError, TypeError):
        return 0


def _chapter_query(ch):
    parts = [str(ch.get("title") or "")]
    parts += [str(x) for x in (ch.get("key_points") or [])]
    parts += [str(x) for x in (ch.get("data_needed") or [])]
    return " ".join(p for p in parts if p)


def _truncate(body, max_words):
    if char_count(body) <= max_words:
        return body, False
    limit = len(body)
    while limit > 0 and char_count(body[:limit]) > max_words:
        limit -= 1
    seg = body[:limit]
    idx = -1
    for sep in ("。", ".", "；", ";"):
        idx = max(idx, seg.rfind(sep))
    if idx > 0:
        seg = seg[:idx + 1]
    return seg, True


def _audit(truth_base, body, chapter_no):
    prompt = AUDIT_PROMPT.format(
        validated_data=_validated_data_text(truth_base["validated_data"]),
        terminology=_terminology_text(truth_base["global_terminology"]),
        chapter_no=chapter_no,
        body=body,
    )
    return llm.call_json(prompt).data or {}


def write_chapter(db, report, truth_base, ch, chapter_no, total, memory):
    title = str(ch.get("title") or f"第{chapter_no}章")
    suggested = int(ch.get("suggested_words") or 0)
    max_words = int(suggested * 1.1) if suggested else 2200

    items = retriever.retrieve(db, _chapter_query(ch), k=6)
    context = "\n\n".join(f"【来源：{it['filename']}】\n{it['text']}" for it in items)
    retrieved_files = list({it["filename"] for it in items})

    base = WRITE_PROMPT.format(
        title=report.title,
        style="正式",
        user_requirements=report.user_requirements or "",
        chapter_no=chapter_no,
        total=total,
        chapter=(f"标题：{title}\n关键论点：{'、'.join(ch.get('key_points') or [])}\n"
                 f"所需数据：{'、'.join(ch.get('data_needed') or [])}\n建议字数：{suggested}"),
        max_words=max_words,
        validated_data=_validated_data_text(truth_base["validated_data"]),
        terminology=_terminology_text(truth_base["global_terminology"]),
        chapter_summaries=memory["summaries_text"],
        last_ending=memory["last_ending"],
        context=context,
    )

    data = llm.call_json(base).data or {}
    body = str(data.get("body") or "")
    summary = str(data.get("summary") or "")[:100]
    missing = [str(x) for x in (data.get("missing") or []) if x]
    user_notice = str(data.get("user_notice") or "")

    truncated = False
    if char_count(body) > max_words:
        data2 = llm.call_json(
            base + COMPRESS_ADDON.format(previous_body=body, previous_words=char_count(body),
                                         max_words=max_words, suggested_words=suggested)
        ).data or {}
        body = str(data2.get("body") or body)
        summary = str(data2.get("summary") or summary)[:100]
        if char_count(body) > max_words:
            body, truncated = _truncate(body, max_words)

    audit = _audit(truth_base, body, chapter_no)
    rewrite_count = 0
    while _critical_count(audit) > 0 and rewrite_count < 2:
        data3 = llm.call_json(
            base + REWRITE_ADDON.format(previous_body=body, audit_report=json.dumps(audit, ensure_ascii=False))
        ).data or {}
        body = str(data3.get("body") or body)
        summary = str(data3.get("summary") or summary)[:100]
        audit = _audit(truth_base, body, chapter_no)
        rewrite_count += 1

    status = "通过" if _critical_count(audit) == 0 else "待人工"
    return {
        "title": title, "body": body, "summary": summary, "missing": missing,
        "user_notice": user_notice, "audit": audit, "rewrite_count": rewrite_count,
        "truncated": 1 if truncated else 0, "retrieved": retrieved_files, "status": status,
    }


def _save_chapter(db, report, ch, chapter_no, result):
    existing = (db.query(models.ChapterRecord)
                .filter(models.ChapterRecord.report_id == report.id,
                        models.ChapterRecord.chapter_id == chapter_no).first())
    fields = dict(
        title=result.get("title") or ch.get("title") or f"第{chapter_no}章",
        body=result.get("body") or "",
        original_body=result.get("body") or "",
        status=result.get("status") or "失败",
        audit_json=json.dumps(result.get("audit") or {}, ensure_ascii=False),
        rewrite_count=result.get("rewrite_count") or 0,
        truncated=result.get("truncated") or 0,
        retrieved_json=json.dumps(result.get("retrieved") or [], ensure_ascii=False),
        missing_json=json.dumps(result.get("missing") or [], ensure_ascii=False),
        summary=result.get("summary") or "",
    )
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.updated_at = datetime.utcnow()
    else:
        db.add(models.ChapterRecord(report_id=report.id, chapter_id=chapter_no, **fields))
    db.commit()


def run_writing(report_id):
    db = _new_session()
    try:
        report = db.get(models.Report, report_id)
        if not report:
            return
        task = get_or_create_task(db, report)
        task.status = "running"
        task.pause_requested = 0
        task.error = None
        db.commit()

        outline_row = db.query(models.Outline).filter(models.Outline.report_id == report_id).first()
        if not outline_row:
            task.status = "failed"
            task.error = "无大纲"
            db.commit()
            return
        chapters = json.loads(outline_row.chapters_json or "[]")
        task.total_chapters = len(chapters)
        db.commit()

        truth_base = load_truth_base(db, report)  # 每份报告只提炼一次；resume 沿用

        done = (db.query(models.ChapterRecord)
                .filter(models.ChapterRecord.report_id == report_id,
                        models.ChapterRecord.status != "失败")
                .order_by(models.ChapterRecord.chapter_id).all())
        summaries = [f"第{c.chapter_id}章：{c.summary}" for c in done if c.summary]
        last_ending = _last_sentence(done[-1].body) if done else ""

        for i, ch in enumerate(chapters, 1):
            existing = (db.query(models.ChapterRecord)
                        .filter(models.ChapterRecord.report_id == report_id,
                                models.ChapterRecord.chapter_id == i).first())
            if existing and existing.status != "失败":
                continue  # 已定稿（通过 / 待人工）跳过，不重写
            db.refresh(task)
            if task.pause_requested:
                task.status = "paused"
                report.status = "paused"
                db.commit()
                return
            task.current_chapter = i
            db.commit()
            memory = {"summaries_text": "\n".join(summaries), "last_ending": last_ending}
            try:
                result = write_chapter(db, report, truth_base, ch, i, len(chapters), memory)
            except ApiError as e:
                task.status = "failed"
                task.error = f"第 {i} 章失败：{e.message}"
                db.commit()
                _save_chapter(db, report, ch, i, {"status": "失败", "body": "", "summary": ""})
                return
            _save_chapter(db, report, ch, i, result)
            last_ending = _last_sentence(result["body"])
            if result.get("summary"):
                summaries.append(f"第{i}章：{result['summary']}")

        task.status = "done"
        task.current_chapter = len(chapters)
        report.status = "done"
        db.commit()
    except Exception as e:  # noqa: 兜底，避免线程静默死亡
        try:
            task = db.query(models.WritingTask).filter(models.WritingTask.report_id == report_id).first()
            if task:
                task.status = "failed"
                task.error = f"内部错误：{type(e).__name__}"
                db.commit()
        except Exception:  # noqa
            pass
    finally:
        db.close()


def spawn(report_id):
    t = threading.Thread(target=run_writing, args=(report_id,), daemon=True)
    t.start()
    return t


def request_pause(db: Session, report_id):
    task = db.query(models.WritingTask).filter(models.WritingTask.report_id == report_id).first()
    if not task:
        raise ApiError("NOT_FOUND", "写任务不存在", 404)
    if task.status == "running":
        task.pause_requested = 1
        db.commit()
    return task
