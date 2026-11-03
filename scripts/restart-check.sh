#!/usr/bin/env bash
# 重启恢复检查钩子：start / write / read / stop（契约见通用手册第十节）
# verify.sh 自己负责起服务→写标记→杀进程→再起→读回比对；本钩子只提供四个动作。
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"
PORT=8011
DATA_DIR="${RESTART_CHECK_DIR:-/tmp/restart-check-default}"

log() { echo "$@" >&2; }

start() {
  mkdir -p "$DATA_DIR"
  if lsof -i :"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    log "端口 $PORT 被占用，不杀他人进程"
    return 1
  fi
  PY="$BACKEND_DIR/.venv/bin/python"
  [ -x "$PY" ] || PY="$(command -v python3)"
  cd "$BACKEND_DIR" || return 1
  DATA_DIR="$DATA_DIR" MODEL_API_KEY="" nohup "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" > "$DATA_DIR/server.log" 2>&1 &
  local pid=$!
  for _ in $(seq 1 40); do
    if curl -s -o /dev/null "http://127.0.0.1:$PORT/api/v1/reports"; then
      echo "$pid"
      return 0
    fi
    sleep 0.25
  done
  log "服务未能在预期时间内启动"
  return 1
}

write() {
  local marker="$1"
  curl -s -X POST "http://127.0.0.1:$PORT/api/v1/reports" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"$marker\",\"target_words\":12000}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])"
}

read() {
  local id="$1"
  curl -s "http://127.0.0.1:$PORT/api/v1/reports/$id" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['title'])"
}

stop() {
  local pids
  pids="$(lsof -ti :"$PORT" 2>/dev/null || true)"
  [ -n "$pids" ] && kill $pids 2>/dev/null || true
  echo "stopped"
}

case "${1:-}" in
  start) start ;;
  write) write "${2:-}" ;;
  read) read "${2:-}" ;;
  stop) stop ;;
  *) echo "用法：$0 {start|write <标记>|read <ID>|stop}" >&2; exit 2 ;;
esac
