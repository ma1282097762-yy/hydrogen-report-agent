import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

# 必须在 import app 之前设置环境
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="testdata-")
os.environ["MODEL_API_KEY"] = "fake-for-test"  # 短于 20 字符，避免被密钥扫描误判
os.environ["MODEL_NAME"] = "deepseek-chat"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    from app import db
    from app.main import app

    db.init_db()
    db.Base.metadata.drop_all(bind=db.engine)
    db.Base.metadata.create_all(bind=db.engine)
    with TestClient(app) as c:
        yield c
