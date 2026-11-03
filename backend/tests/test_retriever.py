import pytest

from app import db as dbm
from app import models
from app.services import retriever


@pytest.fixture()
def session():
    dbm.init_db()
    dbm.Base.metadata.drop_all(bind=dbm.engine)
    dbm.Base.metadata.create_all(bind=dbm.engine)
    s = dbm.SessionLocal()
    yield s
    s.close()


def _add_doc(session, filename, text):
    d = models.Document(owner_id="default", filename=filename, stored_path="/x",
                        file_type="pdf", status="available", chunk_count=1)
    session.add(d)
    session.flush()
    session.add(models.Chunk(document_id=d.id, chunk_index=0, text=text))
    return d


def test_retrieve_keyword(session):
    _add_doc(session, "投资说明.pdf", "本项目总投资为 2.5 亿元，建设期 18 个月。")
    _add_doc(session, "行业报告.pdf", "全国加氢站数量持续增长，行业规模扩大。")
    session.commit()
    results = retriever.retrieve(session, "总投资", k=3)
    assert results
    assert results[0]["filename"] == "投资说明.pdf"


def test_retrieve_empty(session):
    assert retriever.retrieve(session, "总投资", k=3) == []


def test_retrieve_skips_non_available(session):
    _add_doc(session, "扫描件.pdf", "只有图没有文字")
    session.query(models.Document).update({"status": "empty"})
    session.commit()
    assert retriever.retrieve(session, "文字", k=3) == []
