import math
import re
from collections import Counter

from sqlalchemy.orm import Session

from .. import models


def _bigrams(text):
    text = re.sub(r"\s+", "", text or "")
    if len(text) < 2:
        return [text] if text else []
    return [text[i:i + 2] for i in range(len(text) - 1)]


def _tf(grams):
    c = Counter(grams)
    n = len(grams) or 1
    return {g: v / n for g, v in c.items()}


def retrieve(db: Session, query: str, k: int = 6):
    """按字符 bigram TF-IDF 余弦相似度检索最相关段落，返回 [{filename, text, score}]（按 text 去重）。"""
    rows = (db.query(models.Chunk, models.Document)
            .join(models.Document, models.Chunk.document_id == models.Document.id)
            .all())
    docs = [(c, d) for c, d in rows if d.status == "available" and c.text.strip()]
    if not docs:
        return []

    n = len(docs)
    df = Counter()
    tf_list = []
    for c, _d in docs:
        grams = _bigrams(c.text)
        tf_list.append(_tf(grams))
        for g in set(grams):
            df[g] += 1

    q = _tf(_bigrams(query))
    scored = []
    for (c, d), tf in zip(docs, tf_list):
        dot = 0.0
        for g, w in q.items():
            if g in tf:
                dot += w * tf[g] * math.log(1 + n / (1 + df[g]))
        scored.append((dot, d.filename, c.text))
    scored.sort(key=lambda x: -x[0])

    out = []
    seen = set()
    for score, filename, text in scored:
        if not text or text in seen:
            continue
        seen.add(text)
        out.append({"filename": filename, "text": text, "score": round(score, 4)})
        if len(out) >= k:
            break
    return out
