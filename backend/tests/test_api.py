from app.services import llm
from app.services import outline as outline_service


def _txt_body():
    return "这是用于切段的测试文档内容。" * 200


def test_upload_txt_available(client):
    r = client.post("/api/v1/documents", files=[("files", ("test.txt", _txt_body(), "text/plain"))])
    assert r.status_code == 200
    docs = r.json()["documents"]
    assert docs[0]["status"] == "available"
    assert docs[0]["chunk_count"] >= 1


def test_upload_unsupported_format(client):
    r = client.post("/api/v1/documents", files=[("files", ("a.xlsx", b"data", "application/octet-stream"))])
    assert r.status_code == 200
    d = r.json()["documents"][0]
    assert d["status"] == "failed"
    assert "格式不支持" in d["error"]


def test_upload_scanned_pdf_empty(client):
    from io import BytesIO

    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    buf = BytesIO()
    w.write(buf)
    buf.seek(0)
    r = client.post("/api/v1/documents", files=[("files", ("scan.pdf", buf.read(), "application/pdf"))])
    assert r.status_code == 200
    d = r.json()["documents"][0]
    assert d["status"] == "empty"
    assert d["status_label"] == "无文字"


def test_create_report_target_too_big(client):
    r = client.post("/api/v1/reports", json={"title": "x", "target_words": 20000})
    assert r.status_code == 400


def test_create_report_ok(client):
    r = client.post("/api/v1/reports", json={"title": "测试报告", "target_words": 12000})
    assert r.status_code == 200
    assert r.json()["status"] == "draft"
    assert r.json()["status_label"] == "待确认大纲"


def test_generate_outline_and_confirm(client, monkeypatch):
    fake = llm.LLMResult(data={"full_outline": [
        {"chapter_id": i, "title": f"第{i}章", "key_points": ["a"], "data_needed": ["总投资"],
         "suggested_words": 1000} for i in range(1, 11)]})
    monkeypatch.setattr(outline_service.llm, "call_json", lambda *a, **k: fake)

    rep = client.post("/api/v1/reports", json={"title": "测试报告", "target_words": 12000}).json()
    rid = rep["id"]
    g = client.post(f"/api/v1/reports/{rid}/outline/generate")
    assert g.status_code == 200
    outline = g.json()["outline"]
    assert outline["chapter_count"] == 10
    assert outline["total_words"] == 12000
    assert outline["needs_manual"] is False

    c = client.post(f"/api/v1/reports/{rid}/outline/confirm")
    assert c.status_code == 200
    assert c.json()["report"]["status"] == "writing"


def test_confirm_without_outline(client):
    rep = client.post("/api/v1/reports", json={"title": "测试报告", "target_words": 12000}).json()
    c = client.post(f"/api/v1/reports/{rep['id']}/outline/confirm")
    assert c.status_code == 400


def test_error_response_structure(client):
    r = client.get("/api/v1/reports/99999")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body and "code" in body["error"] and "message" in body["error"]
