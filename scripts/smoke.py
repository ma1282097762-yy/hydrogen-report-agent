#!/usr/bin/env python3
"""真实模型冒烟脚本（阶段 2-2）：跑通「创建报告 → 生成大纲 → 提炼关键事实 → 写第 1 章（含审计/重写/压缩）」。

从 backend/.env 读取 MODEL_API_KEY；无 Key 时不写记录、如实打印「待验」。
记录自动追加到 docs/evidence/阶段2-2/冒烟记录.md（每段真实模型契约一行）。
"""
import datetime
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
PRODUCT = Path(__file__).resolve().parent.parent
STAGE = sys.argv[1] if len(sys.argv) > 1 else "阶段2-2"
RECORD = PRODUCT / "docs" / "evidence" / STAGE / "冒烟记录.md"

sys.path.insert(0, str(BACKEND))
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="smoke2-")  # 不污染真实数据

from app import db as dbm  # noqa: E402
from app import models  # noqa: E402
from app.config import settings  # noqa: E402
from app.services import llm as llm_module  # noqa: E402
from app.services import outline as outline_service  # noqa: E402
from app.services import writer  # noqa: E402


def classify(prompt):
    if "数据核对员" in prompt:
        return "关键事实提炼"
    if "技术审计专家" in prompt:
        return "审计"
    if "Rewrite Rules" in prompt:
        return "重写"
    if "Shorten Rules" in prompt:
        return "压缩"
    if "撰稿专家" in prompt:
        return "写章"
    if "咨询顾问" in prompt or "架构设计" in prompt:
        return "生成大纲"
    return "模型调用"


def main():
    if not settings.model_api_key:
        print("待验：未配置 MODEL_API_KEY，跳过真实冒烟（不写记录）")
        return 0

    dbm.init_db()
    session = dbm.SessionLocal()

    doc = models.Document(owner_id="default", filename="立项批复.txt", stored_path="/tmp/smoke.txt",
                          file_type="txt", status="available", chunk_count=1)
    session.add(doc)
    session.flush()
    session.add(models.Chunk(document_id=doc.id, chunk_index=0,
                            text="本项目为攀枝花市钒钛高新区制氢加氢一体化示范项目（一期），"
                                 "总投资 25000 万元，建设期 18 个月，加氢站加注压力 35 MPa。"))
    session.commit()

    report = models.Report(owner_id="default", title="冒烟测试报告", target_words=3000,
                           user_requirements="", status="draft")
    session.add(report)
    session.commit()
    session.refresh(report)

    records = []
    orig = llm_module.call_json

    def wrapped(prompt, *a, **k):
        r = orig(prompt, *a, **k)
        records.append((classify(prompt), r))
        return r

    llm_module.call_json = wrapped
    outcome = "通过"
    try:
        odata, _ = outline_service.generate_outline(report)
        report.status = "writing"
        session.commit()
        truth = writer.extract_truth_base(session, report)
        ch = odata.chapters[0].model_dump()
        result = writer.write_chapter(session, report, truth, ch, 1, len(odata.chapters),
                                      {"summaries_text": "", "last_ending": ""})
        if result["status"] == "待人工":
            outcome = "瑕疵待打分"
        elif result["status"] != "通过":
            outcome = "失败"
    except Exception as e:  # noqa
        outcome = "失败"
        print("冒烟异常：", type(e).__name__, e)
    finally:
        llm_module.call_json = orig

    write_rows(records, outcome)
    session.close()
    print("冒烟完成：", outcome)
    return 0


def write_rows(records, outcome):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    if not RECORD.exists():
        RECORD.write_text(
            "# 冒烟记录（冒烟脚本自动写入，不得手填）\n"
            "- 产品：可研报告生成Agent\n"
            f"- 阶段：{STAGE}\n"
            f"- 模型：{settings.model_name}\n"
            f"- 写入时间：{now}\n\n"
            "| 时间 | 链路 | 请求 ID | 输入 token | 输出 token | 首字耗时 | 总耗时 | 结构校验 | 重试次数 | 结果 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
    with open(RECORD, "a", encoding="utf-8") as f:
        for i, (step, r) in enumerate(records):
            struct = "首测合规" if r.retries == 0 else "重试后合规"
            row_result = "通过"
            if step == "写章" and outcome == "瑕疵待打分":
                row_result = "瑕疵待打分"
            if outcome == "失败":
                row_result = "失败"
            f.write(f"| {now} | {step} | {r.request_id} | {r.tokens_in} | {r.tokens_out} | - | {r.duration_s}s | {struct} | {r.retries} | {row_result} |\n")


if __name__ == "__main__":
    sys.exit(main())
