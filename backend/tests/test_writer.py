import pytest

from app import db as dbm
from app import models
from app.services import writer, llm
from app.services.parsing import char_count


@pytest.fixture()
def session():
    dbm.init_db()
    dbm.Base.metadata.drop_all(bind=dbm.engine)
    dbm.Base.metadata.create_all(bind=dbm.engine)
    s = dbm.SessionLocal()
    yield s
    s.close()


@pytest.fixture()
def report(session):
    r = models.Report(owner_id="default", title="测试报告", target_words=3000,
                      user_requirements="", status="writing")
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


def _r(data):
    return llm.LLMResult(data=data)


TRUTH = {"validated_data": {}, "sources": {}, "global_terminology": []}
MEM = {"summaries_text": "", "last_ending": ""}


def test_validate_truth_base():
    raw = {
        "validated_data": {"total_investment": "2.5亿元", "extra_field": "x", "dc_power_consumption": 123},
        "sources": {"total_investment": "批复.pdf"},
        "global_terminology": ["PEM电解槽", 123],
    }
    v = writer._validate_truth_base(raw)
    assert v["validated_data"]["total_investment"] == "2.5亿元"
    assert v["validated_data"]["dc_power_consumption"] is None  # 非字符串 → null
    assert "extra_field" not in v["validated_data"]  # 多出的字段丢掉
    assert v["sources"]["total_investment"] == "批复.pdf"
    assert v["global_terminology"] == ["PEM电解槽"]  # 非字符串过滤


def test_last_sentence():
    assert writer._last_sentence("第一句。第二句。第三句。") == "第三句。"
    assert writer._last_sentence("无标点结尾") == "无标点结尾"


def test_truncate_at_last_sentence():
    body = "这是很长的一句。" * 300
    out, trunc = writer._truncate(body, 60)
    assert trunc is True
    assert char_count(out) <= 60
    assert out.rstrip().endswith("。")


def test_write_chapter_happy_path(report, session, monkeypatch):
    calls = [_r({"body": "本章正文内容。", "summary": "摘要", "missing": [], "user_notice": ""}),
             _r({"critical_count": 0, "warning_count": 0, "issues": [], "unverifiable": []})]
    monkeypatch.setattr(writer.llm, "call_json", lambda *a, **k: calls.pop(0))
    ch = {"title": "第一章", "key_points": ["a"], "data_needed": ["总投资"], "suggested_words": 500}
    result = writer.write_chapter(session, report, TRUTH, ch, 1, 3, MEM)
    assert result["status"] == "通过"
    assert result["rewrite_count"] == 0
    assert result["truncated"] == 0


def test_write_chapter_critical_cap(report, session, monkeypatch):
    crit = {"critical_count": 1, "warning_count": 0,
            "issues": [{"severity": "CRITICAL", "quote": "x", "expected": "y", "basis": "total_investment"}],
            "unverifiable": []}
    calls = [_r({"body": "正文一。", "summary": "s", "missing": [], "user_notice": ""}), _r(crit),
             _r({"body": "正文二。", "summary": "s", "missing": [], "user_notice": ""}), _r(crit),
             _r({"body": "正文三。", "summary": "s", "missing": [], "user_notice": ""}), _r(crit)]
    monkeypatch.setattr(writer.llm, "call_json", lambda *a, **k: calls.pop(0))
    ch = {"title": "第一章", "key_points": [], "data_needed": [], "suggested_words": 500}
    result = writer.write_chapter(session, report, TRUTH, ch, 1, 3, MEM)
    assert result["status"] == "待人工"
    assert result["rewrite_count"] == 2


def test_write_chapter_compress_then_truncate(report, session, monkeypatch):
    long_body = "这是很长的一段文字。" * 300
    calls = [_r({"body": long_body, "summary": "s", "missing": [], "user_notice": ""}),
             _r({"body": long_body, "summary": "s", "missing": [], "user_notice": ""}),  # 压缩后仍超
             _r({"critical_count": 0, "issues": [], "unverifiable": []})]
    monkeypatch.setattr(writer.llm, "call_json", lambda *a, **k: calls.pop(0))
    ch = {"title": "第一章", "key_points": [], "data_needed": [], "suggested_words": 100}  # 上限 110
    result = writer.write_chapter(session, report, TRUTH, ch, 1, 3, MEM)
    assert result["truncated"] == 1
    assert char_count(result["body"]) <= 110


def test_load_truth_base_extracts_once(report, session, monkeypatch):
    calls = [_r({"validated_data": {"total_investment": "2.5亿元"},
                 "sources": {"total_investment": "a.pdf"}, "global_terminology": []})]
    monkeypatch.setattr(writer.llm, "call_json", lambda *a, **k: calls.pop(0))
    t1 = writer.load_truth_base(session, report)
    t2 = writer.load_truth_base(session, report)  # 不再调模型（calls 已空，若再调会 IndexError）
    assert t1 == t2
