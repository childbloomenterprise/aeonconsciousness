"""Live dashboard: watch AEON develop, then secretly sabotage its body."""

from __future__ import annotations

import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .agent import AeonConfig
from .experiment import CONDITIONS
from .session import Session
from .story import GuidedStory

STATIC = Path(__file__).with_name("static")


class LiveRunner:
    def __init__(self, seed: int = 0, condition: str = "intact", tps: float = 15.0) -> None:
        self.lock = threading.Lock()
        self.tps = tps
        self.paused = False
        self.story: GuidedStory | None = None
        self.reset(seed, condition)
        threading.Thread(target=self._loop, daemon=True).start()

    def reset(self, seed: int, condition: str) -> None:
        spec = CONDITIONS[condition]
        cfg = AeonConfig(seed=seed, label=condition, **spec["config"])
        with self.lock:
            self.condition = condition
            self.session = Session(seed, cfg, agent_cls=spec["cls"], live=True)
            self.story = None
            self.paused = False

    def start_story(self, seed: int) -> None:
        self.reset(seed, "intact")
        with self.lock:
            self.story = GuidedStory(self.session)
            self.tps = max(self.tps, 25.0)

    def _loop(self) -> None:
        while True:
            start = time.time()
            if not self.paused:
                with self.lock:
                    self.session.step()
                    if self.story:
                        self.story.tick()
            time.sleep(max(0.0, 1.0 / max(self.tps, 0.5) - (time.time() - start)))

    def state(self) -> dict[str, Any]:
        with self.lock:
            s = self.session
            agent, world = s.agent, s.world
            truth = world.truth_channel_map()
            hc = agent.sm.hand_channels
            swap = bool(hc) and hc[0] == truth["hand_y"]
            return {
                "condition": self.condition,
                "conditions": list(CONDITIONS),
                "seed": s.seed,
                "paused": self.paused,
                "tps": self.tps,
                "frame_swap": swap,
                "world": world.snapshot(),
                "truth_channels": truth,
                "agent": agent.snapshot(),
                "interventions": s.interventions[-10:],
                "story": None if self.story is None else {
                    "step": self.story.step, "caption": self.story.caption, "detail": self.story.detail,
                    "done": self.story.done, "results": self.story.results,
                },
            }


def make_handler(runner: LiveRunner) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: Any) -> None:
            return

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data: Any, code: int = 200) -> None:
            self._send(code, json.dumps(data, default=str).encode(), "application/json")

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                self._json(runner.state())
            else:
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._json({"error": "invalid json"}, 400)
            try:
                if self.path == "/api/intervene":
                    kind = str(body.pop("kind"))
                    with runner.lock:
                        runner.session.intervene(kind, **body)
                elif self.path == "/api/control":
                    action = body.get("action")
                    if action == "pause":
                        runner.paused = True
                    elif action == "resume":
                        runner.paused = False
                    elif action == "speed":
                        runner.tps = float(body.get("tps", 15))
                    elif action == "story":
                        runner.start_story(int(body.get("seed", 0)))
                    elif action == "reset":
                        runner.reset(int(body.get("seed", 0)), str(body.get("condition", "intact")))
                    else:
                        return self._json({"error": "unknown action"}, 400)
                else:
                    return self._json({"error": "not found"}, 404)
            except (KeyError, ValueError, TypeError) as exc:
                return self._json({"error": str(exc)}, 400)
            self._json({"ok": True})

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8770, seed: int = 0, condition: str = "intact", tps: float = 15.0) -> None:
    runner = LiveRunner(seed, condition, tps)
    server = ThreadingHTTPServer((host, port), make_handler(runner))
    print(f"AEON developmental dashboard on http://{host}:{port}")
    server.serve_forever()
