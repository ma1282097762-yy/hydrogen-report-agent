import re
import uuid
from pathlib import Path

from ..config import settings

ALLOWED_EXTS = {".pdf", ".docx", ".md", ".txt", ".markdown"}
# 扫描件判定：平均每页提取到的文字少于该值，视为「无文字，检索不到」
MIN_AVG_CHARS_PER_PAGE = 50


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8", "gb18030", "utf-16"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def extract_text(path: Path, ext: str):
    """返回 (文本, 失败原因或 None)。空文本返回 ''，由调用方判定为「无文字」。"""
    if ext in (".txt", ".md", ".markdown"):
        return _read_text_file(path), None

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return "", "缺少 pypdf 库"
        try:
            reader = PdfReader(str(path))
            pages = [(p.extract_text() or "") for p in reader.pages]
            if not pages:
                return "", None
            avg = sum(len(p) for p in pages) / len(pages)
            if avg < MIN_AVG_CHARS_PER_PAGE:
                return "", None  # 扫描件 / 图片型 PDF
            return "\n\n".join(pages), None
        except Exception as e:  # noqa
            return "", f"PDF 解析失败：{type(e).__name__}"

    if ext == ".docx":
        try:
            import docx
        except ImportError:
            return "", "缺少 python-docx 库"
        try:
            d = docx.Document(str(path))
            parts = [p.text for p in d.paragraphs if p.text.strip()]
            for table in d.tables:
                for row in table.rows:
                    parts.append(" ".join(c.text for c in row.cells))
            return "\n".join(parts), None
        except Exception as e:  # noqa
            return "", f"Word 解析失败：{type(e).__name__}"

    return "", "当前格式不支持，请上传 PDF、Word、Markdown 或 TXT"


def chunk_text(text: str, size: int = None, overlap: int = None):
    size = size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        chunks.append(text[start:end])
        if end >= n:
            break
        start = end - overlap
        if start <= 0 or start >= n:
            break
    return chunks


def char_count(text: str) -> int:
    """字数统计口径：去掉空格和换行后的字符数（PRD 第五节）。"""
    return len(re.sub(r"\s", "", text or ""))


def safe_store_name(ext: str) -> str:
    return f"{uuid.uuid4().hex}{ext}"
