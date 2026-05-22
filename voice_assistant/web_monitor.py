"""Small read-only web monitor for the voice assistant runtime."""

from __future__ import annotations

from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
from typing import Any, TextIO


SECRET_KEY_MARKERS = (
    "API_KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASS",
    "CONNECTION_STRING",
)
IGNORED_OSC_READ_PATHS = ("/xremote", "/xinfo")


def redact_config_value(key: str, value: Any) -> Any:
    """Mask sensitive values while keeping non-secret runtime configuration visible."""
    upper_key = key.upper()
    if any(marker in upper_key for marker in SECRET_KEY_MARKERS):
        if value in (None, ""):
            return value
        return "***redacted***"
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_config_value(key, item) for item in value]
    return value


def redact_mapping(values: dict[str, Any]) -> dict[str, Any]:
    return {key: redact_config_value(key, value) for key, value in values.items()}


class TeeStream:
    """Mirror writes to the original stream and to the monitor log buffer."""

    def __init__(self, original: TextIO, monitor: "WebMonitor", stream_name: str):
        self.original = original
        self.monitor = monitor
        self.stream_name = stream_name

    def write(self, value: str) -> int:
        written = self.original.write(value)
        self.monitor.append_log(value, source=self.stream_name)
        return written

    def flush(self) -> None:
        self.original.flush()

    def isatty(self) -> bool:
        return self.original.isatty()

    def fileno(self) -> int:
        return self.original.fileno()

    @property
    def encoding(self) -> str | None:
        return self.original.encoding

    def __getattr__(self, name: str) -> Any:
        return getattr(self.original, name)


class WebMonitor:
    """Thread-safe runtime state served over a tiny local HTTP server."""

    def __init__(self, max_log_chars: int = 200_000):
        self.max_log_chars = max_log_chars
        self._lock = threading.RLock()
        self._log_chunks: deque[str] = deque()
        self._log_chars = 0
        self._injected_commands: deque[str] = deque()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._stdout_original: TextIO | None = None
        self._stderr_original: TextIO | None = None
        self._started_at = time.time()
        self._snapshot: dict[str, Any] = {
            "mode": "unknown",
            "env_file": None,
            "internet": "unknown",
            "services": {},
            "config": {},
            "config_text": "{}",
            "prompt": "",
            "updated_at": time.time(),
        }

    def install_console_capture(self) -> None:
        with self._lock:
            if self._stdout_original is not None:
                return
            self._stdout_original = sys.stdout
            self._stderr_original = sys.stderr
            sys.stdout = TeeStream(sys.stdout, self, "stdout")
            sys.stderr = TeeStream(sys.stderr, self, "stderr")

    def restore_console_capture(self) -> None:
        with self._lock:
            if self._stdout_original is not None:
                sys.stdout = self._stdout_original
                self._stdout_original = None
            if self._stderr_original is not None:
                sys.stderr = self._stderr_original
                self._stderr_original = None

    def start(self, host: str = "127.0.0.1", port: int = 8765) -> tuple[str, int]:
        with self._lock:
            if self._server:
                return self._server.server_address

            monitor = self

            class MonitorHandler(BaseHTTPRequestHandler):
                def do_GET(self) -> None:
                    if self.path in {"/", "/index.html"}:
                        self._send_text(INDEX_HTML, "text/html; charset=utf-8")
                        return
                    if self.path == "/api/snapshot":
                        self._send_json(monitor.snapshot())
                        return
                    self.send_error(404)

                def do_POST(self) -> None:
                    if self.path == "/api/inject-command":
                        self._handle_inject_command()
                        return
                    self.send_error(404)

                def log_message(self, format: str, *args: Any) -> None:
                    return

                def _send_text(self, value: str, content_type: str) -> None:
                    encoded = value.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)

                def _send_json(self, value: dict[str, Any]) -> None:
                    encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)

                def _handle_inject_command(self) -> None:
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                    except ValueError:
                        length = 0

                    raw_body = self.rfile.read(min(length, 16_384))
                    try:
                        payload = json.loads(raw_body.decode("utf-8") or "{}")
                    except json.JSONDecodeError:
                        self.send_error(400, "Invalid JSON")
                        return

                    command = str(payload.get("command") or "").strip()
                    if not command:
                        self.send_error(400, "Command is required")
                        return

                    monitor.inject_command(command)
                    self._send_json({"accepted": True})

            self._server = ThreadingHTTPServer((host, port), MonitorHandler)
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                name="voice-assistant-web-monitor",
                daemon=True,
            )
            self._thread.start()
            return self._server.server_address

    def stop(self) -> None:
        with self._lock:
            server = self._server
            thread = self._thread
            self._server = None
            self._thread = None

        if server:
            server.shutdown()
            server.server_close()
        if thread:
            thread.join(timeout=2)

    def append_log(self, value: str, source: str = "stdout") -> None:
        if not value:
            return

        filtered_value = self._filter_log_value(value)
        if not filtered_value:
            return

        with self._lock:
            self._log_chunks.append(filtered_value)
            self._log_chars += len(filtered_value)
            while self._log_chars > self.max_log_chars and self._log_chunks:
                self._log_chars -= len(self._log_chunks.popleft())
            self._snapshot["updated_at"] = time.time()

    def inject_command(self, command: str) -> None:
        cleaned_command = command.strip()
        if not cleaned_command:
            return

        with self._lock:
            self._injected_commands.append(cleaned_command)
            self._snapshot["updated_at"] = time.time()

    def pop_injected_command(self) -> str | None:
        with self._lock:
            if not self._injected_commands:
                return None
            self._snapshot["updated_at"] = time.time()
            return self._injected_commands.popleft()

    def _filter_log_value(self, value: str) -> str:
        lines = value.splitlines(keepends=True)
        if not lines:
            return ""
        return "".join(line for line in lines if not self._should_skip_log_line(line))

    def _should_skip_log_line(self, line: str) -> bool:
        if "[OSC READ]" not in line:
            return False
        return any(line.rstrip().endswith(path) for path in IGNORED_OSC_READ_PATHS)

    def update(
        self,
        *,
        mode: str | None = None,
        env_file: str | Path | None = None,
        internet: str | bool | None = None,
        services: dict[str, dict[str, str]] | None = None,
        env_values: dict[str, Any] | None = None,
        mcp_config: dict[str, Any] | None = None,
        prompt: str | None = None,
    ) -> None:
        with self._lock:
            if mode is not None:
                self._snapshot["mode"] = mode
            if env_file is not None:
                self._snapshot["env_file"] = str(env_file)
            if internet is not None:
                if isinstance(internet, bool):
                    self._snapshot["internet"] = "online" if internet else "offline"
                else:
                    self._snapshot["internet"] = internet
            if services is not None:
                merged_services = dict(self._snapshot.get("services") or {})
                merged_services.update(services)
                self._snapshot["services"] = merged_services
            if env_values is not None or mcp_config is not None:
                config = dict(self._snapshot.get("config") or {})
                if env_values is not None:
                    config["env"] = redact_mapping(env_values)
                if mcp_config is not None:
                    config["mcp"] = redact_mapping(mcp_config)
                self._snapshot["config"] = config
                self._snapshot["config_text"] = json.dumps(config, ensure_ascii=False, indent=2)
            if prompt is not None:
                self._snapshot["prompt"] = prompt
            self._snapshot["updated_at"] = time.time()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            snapshot = dict(self._snapshot)
            snapshot["logs"] = "".join(self._log_chunks)
            snapshot["uptime_seconds"] = int(time.time() - self._started_at)
            return snapshot


def build_service_state(
    *,
    llm_provider: str,
    model: str,
    stt_provider: str,
    tts_provider: str,
    mcp_config: dict[str, Any] | None,
    mcp_status: str = "configured",
) -> dict[str, dict[str, str]]:
    server_names = sorted((mcp_config or {}).get("mcpServers", {}).keys())
    mcp_detail = ", ".join(server_names) if server_names else "no configured servers"
    return {
        "LLM": {"status": "configured", "detail": f"{llm_provider} / {model}"},
        "STT": {"status": "configured", "detail": stt_provider},
        "TTS": {"status": "configured", "detail": tts_provider},
        "MCP": {"status": mcp_status, "detail": mcp_detail},
    }


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Live Stage Assistant Monitor</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --text: #1f2528;
      --muted: #626d73;
      --border: #d7dddf;
      --accent: #0f6b62;
      --ok: #1f9d55;
      --warn: #c77900;
      --bad: #c73b3b;
      --idle: #8a9499;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #17191a;
        --panel: #202426;
        --text: #edf1f2;
        --muted: #a8b0b4;
        --border: #384044;
      }
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      border-bottom: 1px solid var(--border);
      background: var(--panel);
    }
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 650;
    }
    main {
      width: min(1180px, calc(100vw - 32px));
      margin: 22px auto;
      display: grid;
      gap: 14px;
    }
    section {
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel);
      overflow: hidden;
    }
    summary {
      cursor: pointer;
      padding: 12px 14px;
      font-weight: 650;
      border-bottom: 1px solid var(--border);
    }
    details:not([open]) summary { border-bottom: 0; }
    .state {
      padding: 14px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 10px;
    }
    .inject-form {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      padding: 14px;
    }
    input {
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0 10px;
      background: color-mix(in srgb, var(--panel) 92%, var(--bg));
      color: var(--text);
      font: inherit;
      outline: none;
    }
    input:focus {
      border-color: var(--accent);
    }
    button {
      min-height: 38px;
      border: 1px solid var(--accent);
      border-radius: 8px;
      padding: 0 14px;
      background: var(--accent);
      color: white;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
    }
    button:disabled {
      opacity: 0.55;
      cursor: default;
    }
    .tile {
      min-height: 74px;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 11px;
      display: grid;
      gap: 4px;
    }
    .tile-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 650;
    }
    .led {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--idle);
      box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 12%, transparent);
      flex: 0 0 auto;
    }
    .ok { background: var(--ok); }
    .warn { background: var(--warn); }
    .bad { background: var(--bad); }
    .idle { background: var(--idle); }
    .detail, .meta {
      color: var(--muted);
      overflow-wrap: anywhere;
    }
    .meta {
      font-size: 12px;
      text-align: right;
    }
    textarea {
      display: block;
      width: 100%;
      min-height: 220px;
      resize: vertical;
      border: 0;
      border-top: 1px solid var(--border);
      padding: 12px;
      background: color-mix(in srgb, var(--panel) 92%, var(--bg));
      color: var(--text);
      font: 12px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      outline: none;
    }
    #logs { min-height: 360px; }
    #prompt { min-height: 300px; }
  </style>
</head>
<body>
  <header>
    <h1>Live Stage Assistant Monitor</h1>
    <div class="meta" id="meta">connecting...</div>
  </header>
  <main>
    <section>
      <details open>
        <summary>Inject Command</summary>
        <form class="inject-form" id="inject-form">
          <input id="inject-command" autocomplete="off">
          <button id="inject-submit" type="submit">Send</button>
        </form>
      </details>
    </section>
    <section>
      <details open>
        <summary>State</summary>
        <div class="state" id="state"></div>
      </details>
    </section>
    <section>
      <details>
        <summary>Config</summary>
        <textarea id="config" readonly spellcheck="false"></textarea>
      </details>
    </section>
    <section>
      <details open>
        <summary>Console Log</summary>
        <textarea id="logs" readonly spellcheck="false"></textarea>
      </details>
    </section>
    <section>
      <details>
        <summary>Prompt</summary>
        <textarea id="prompt" readonly spellcheck="false"></textarea>
      </details>
    </section>
  </main>
  <script>
    const stateEl = document.querySelector("#state");
    const configEl = document.querySelector("#config");
    const logsEl = document.querySelector("#logs");
    const promptEl = document.querySelector("#prompt");
    const metaEl = document.querySelector("#meta");
    const injectForm = document.querySelector("#inject-form");
    const injectCommand = document.querySelector("#inject-command");
    const injectSubmit = document.querySelector("#inject-submit");

    function ledClass(status) {
      const value = String(status || "unknown").toLowerCase();
      if (["online", "initialized", "ready", "ok", "configured"].includes(value)) return "ok";
      if (["initializing", "reload", "unknown"].includes(value)) return "warn";
      if (["offline", "error", "failed"].includes(value)) return "bad";
      return "idle";
    }

    function tile(title, status, detail) {
      return `<div class="tile">
        <div class="tile-title"><span class="led ${ledClass(status)}"></span><span>${title}</span></div>
        <div>${status || "unknown"}</div>
        <div class="detail">${detail || ""}</div>
      </div>`;
    }

    async function refresh() {
      try {
        const response = await fetch("/api/snapshot", { cache: "no-store" });
        const data = await response.json();
        const services = data.services || {};
        const rows = [
          tile("Internet", data.internet, data.mode === "auto" ? "auto profile detection" : "fixed profile"),
          tile("Profile", data.mode, data.env_file || ""),
          ...Object.entries(services).map(([name, service]) => tile(name, service.status, service.detail))
        ];
        stateEl.innerHTML = rows.join("");
        configEl.value = data.config_text || "";
        promptEl.value = data.prompt || "";
        const shouldStick = logsEl.scrollTop + logsEl.clientHeight >= logsEl.scrollHeight - 8;
        logsEl.value = data.logs || "";
        if (shouldStick) logsEl.scrollTop = logsEl.scrollHeight;
        const updated = data.updated_at ? new Date(data.updated_at * 1000).toLocaleTimeString() : "unknown";
        metaEl.textContent = `updated ${updated} · uptime ${data.uptime_seconds || 0}s`;
      } catch (error) {
        metaEl.textContent = `disconnected: ${error}`;
      }
    }

    refresh();
    setInterval(refresh, 1500);

    injectForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const command = injectCommand.value.trim();
      if (!command) return;

      injectSubmit.disabled = true;
      try {
        const response = await fetch("/api/inject-command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command })
        });
        if (!response.ok) throw new Error(await response.text());
        injectCommand.value = "";
        await refresh();
      } catch (error) {
        metaEl.textContent = `inject failed: ${error}`;
      } finally {
        injectSubmit.disabled = false;
        injectCommand.focus();
      }
    });
  </script>
</body>
</html>
"""
