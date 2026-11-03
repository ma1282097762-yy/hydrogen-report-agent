from app.services.parsing import char_count, chunk_text, extract_text


def test_char_count_ignores_whitespace():
    assert char_count("a b\nc") == 3
    assert char_count("总投资 2.5 亿元") == 8  # 去掉空格后 8 个字符


def test_chunk_text_size_and_overlap():
    text = "字" * 2500
    chunks = chunk_text(text, size=800, overlap=100)
    assert len(chunks) == 4
    for c in chunks[:-1]:
        assert len(c) == 800
    # 相邻块重叠 100 字
    assert chunks[1][:100] == chunks[0][-100:]
    assert len(chunks[-1]) <= 800


def test_chunk_text_short():
    assert chunk_text("短文本", size=800, overlap=100) == ["短文本"]
    assert chunk_text("", size=800, overlap=100) == []


def test_extract_txt(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("这是测试内容。" * 100, encoding="utf-8")
    text, err = extract_text(p, ".txt")
    assert err is None
    assert "测试内容" in text


def test_extract_scanned_pdf_is_empty(tmp_path):
    from pypdf import PdfWriter

    p = tmp_path / "scan.pdf"
    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    with open(p, "wb") as f:
        w.write(f)
    text, err = extract_text(p, ".pdf")
    assert err is None
    assert text == ""


def test_extract_docx(tmp_path):
    import docx

    p = tmp_path / "d.docx"
    d = docx.Document()
    d.add_paragraph("这是第一段内容。")
    d.add_paragraph("这是第二段内容。")
    d.save(str(p))
    text, err = extract_text(p, ".docx")
    assert err is None
    assert "第一段内容" in text
