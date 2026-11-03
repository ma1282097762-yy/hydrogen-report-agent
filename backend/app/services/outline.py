from ..prompts import OUTLINE_PROMPT, OUTLINE_TEMPLATE
from ..schemas import OutlineChapter, OutlineData
from . import llm


def _scale_words(chapters, target_words):
    """各章建议字数之和调平到目标字数（PRD F4 程序校验）。"""
    total = sum(c.suggested_words for c in chapters)
    if total <= 0 or total == target_words or not chapters:
        return chapters
    scale = target_words / total
    acc = 0
    for c in chapters[:-1]:
        c.suggested_words = round(c.suggested_words * scale)
        acc += c.suggested_words
    chapters[-1].suggested_words = target_words - acc  # 最后一章吸收舍入误差
    return chapters


def normalize_chapters(raw_items, target_words, allow_scale=True) -> OutlineData:
    """把模型输出（或用户编辑后的章节列表）规范化：重编号、字段清洗、字数调平、章数校验。"""
    chapters = []
    for i, it in enumerate(raw_items, 1):
        if not isinstance(it, dict):
            it = it.model_dump() if hasattr(it, "model_dump") else {}
        title = str(it.get("title") or "").strip() or f"第{i}章"
        chapters.append(OutlineChapter(
            chapter_id=i,
            title=title,
            key_points=[str(x) for x in (it.get("key_points") or [])][:6],
            data_needed=[str(x) for x in (it.get("data_needed") or [])],
            suggested_words=max(0, int(it.get("suggested_words") or 0)),
        ))
    if allow_scale and chapters:
        chapters = _scale_words(chapters, target_words)
    total = sum(c.suggested_words for c in chapters)
    needs_manual = not (8 <= len(chapters) <= 13)
    return OutlineData(
        chapters=chapters,
        total_words=total,
        chapter_count=len(chapters),
        needs_manual=needs_manual,
        message="",
    )


def generate_outline(report):
    """生成大纲；章数不在 8–13 时自动重新生成一次，仍不符则带提示返回（PRD F4）。"""
    prompt = OUTLINE_PROMPT.format(
        title=report.title,
        domain="氢能",
        style="正式",
        target_words=report.target_words,
        user_requirements=report.user_requirements or "",
        template=OUTLINE_TEMPLATE,
    )
    result = llm.call_json(prompt)
    data = normalize_chapters(result.data.get("full_outline") or [], report.target_words)
    if data.needs_manual:
        result2 = llm.call_json(prompt)
        data2 = normalize_chapters(result2.data.get("full_outline") or [], report.target_words)
        if not data2.needs_manual:
            data, result = data2, result2
        else:
            data.message = "章数不在 8–13，请手动增删"
    return data, result
