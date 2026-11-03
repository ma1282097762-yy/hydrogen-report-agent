# 可研报告生成 Agent

帮国华公司氢能研究员把可研报告从 5~6 人日压到 ≤2 人日的 AI 写作工具。核心要求：数字不能错、全文 < 2 万字。

## 目录

- `backend/`：FastAPI 后端（资料上传/解析、创建报告、生成大纲、一键写全文）
- `frontend/`：Next.js 前端（Auros 深色风格）
- `scripts/`：真实模型冒烟脚本、重启恢复检查钩子

## 启动

### 后端（端口 8000）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 填入 MODEL_API_KEY（DeepSeek）
uvicorn app.main:app --reload --port 8000
```

### 前端（端口 3000）

```bash
cd frontend
npm install
cp .env.example .env.local    # 默认 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
npm run dev
```

浏览器打开 http://localhost:3000

## 验证

```bash
# 后端 mock 测试
cd backend && .venv/bin/python -m pytest -q

# 前端检查（lint / 类型 / 构建 / 测试）
cd frontend && npm run lint && npx tsc --noEmit && npm run build && npm test

# 真实模型冒烟（需先配好 DeepSeek Key）
backend/.venv/bin/python scripts/smoke.py
```

## 说明

- 数据存本地 SQLite（`backend/data/app.db`，已被 .gitignore 忽略）；上传文件存 `backend/data/uploads/`。
- 模型：DeepSeek `deepseek-chat`（OpenAI 兼容接口），Key 只放本地 `.env`，不进仓库。
