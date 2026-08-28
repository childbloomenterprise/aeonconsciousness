from __future__ import annotations

import ipaddress
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .ledger import EventLedger


DASHBOARD_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AEON World Monitor</title>
<style>
:root{font-family:Inter,Segoe UI,sans-serif;color-scheme:dark;background:#0b1020;color:#e8edf8}
body{margin:0;padding:20px}header{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}
h1{font-size:22px;margin:0}button{background:#243454;color:#fff;border:1px solid #48618d;padding:8px 12px;border-radius:7px;cursor:pointer}
button.stop{background:#6b2430}.status{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}.metric{background:#131c31;border:1px solid #253451;padding:12px 14px;border-radius:9px;min-width:120px}
.label{font-size:12px;color:#98a7c4}.value{font-size:20px;margin-top:4px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.panel{background:#11192c;border:1px solid #253451;border-radius:9px;padding:14px}.panel h2{font-size:15px;margin:0 0 10px}
.entity img{width:100%;aspect-ratio:4/3;object-fit:cover;background:#070b14;border-radius:6px}.entity pre{white-space:pre-wrap;word-break:break-word;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;padding:8px;border-bottom:1px solid #253451;vertical-align:top}th{color:#98a7c4}
.ok{color:#6ee7a8}.bad{color:#ff8095}@media(max-width:600px){body{padding:12px}.events{overflow-x:auto}}
</style></head><body>
<header><div><h1>AEON World Monitor</h1><div class="label" id="run-id">No run</div></div>
<div><button onclick="control('run')">Resume</button> <button onclick="control('pause')">Pause</button> <button class="stop" onclick="control('stop')">Stop</button></div></header>
<div class="status"><div class="metric"><div class="label">Status</div><div class="value" id="status">—</div></div><div class="metric"><div class="label">Tick</div><div class="value" id="tick">0</div></div><div class="metric"><div class="label">Last heartbeat</div><div class="value" id="updated">—</div></div><div class="metric"><div class="label">Audit</div><div class="value" id="audit">—</div></div><div class="metric"><div class="label">Action success</div><div class="value" id="success">—</div></div><div class="metric"><div class="label">Model errors</div><div class="value" id="errors">0</div></div><div class="metric"><div class="label">Denied actions</div><div class="value" id="denied">0</div></div><div class="metric"><div class="label">Self-model reports</div><div class="value" id="self-reports">0</div></div></div>
<div class="grid" id="entities"></div>
<div class="panel events" style="margin-top:14px"><h2>Live event stream</h2><table><thead><tr><th>Seq</th><th>Tick</th><th>Entity</th><th>Event</th><th>Detail</th><th>Time</th></tr></thead><tbody id="events"></tbody></table></div>
<script>
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function control(command){await fetch('/api/control/'+command,{method:'POST'});await refresh()}
function detail(e){const p=e.payload||{};if(e.event_type==='decision')return `${p.action||''} · ${p.decision_summary||p.prediction||''}`;if(e.event_type==='action_result')return `${p.action||''} · ${p.success?'success':'failed'} ${p.error_message||''}`;if(e.event_type==='model_error'||e.event_type==='world_error')return p.error||'';if(e.event_type==='action_denied')return p.reason||'';return ''}
async function refresh(){try{const data=await(await fetch('/api/status')).json();const run=data.run;if(!run)return;const metrics=data.metrics||{};const counts=metrics.event_counts||{};document.getElementById('run-id').textContent=run.run_id;document.getElementById('status').textContent=run.status;document.getElementById('tick').textContent=run.tick;document.getElementById('updated').textContent=new Date(run.updated_at).toLocaleTimeString();document.getElementById('audit').innerHTML=data.audit_valid?'<span class="ok">valid</span>':'<span class="bad">invalid</span>';document.getElementById('success').textContent=metrics.action_success_rate==null?'—':`${Math.round(metrics.action_success_rate*100)}%`;document.getElementById('errors').textContent=counts.model_error||0;document.getElementById('denied').textContent=counts.action_denied||0;document.getElementById('self-reports').textContent=metrics.self_model_reports||0;
const entities=document.getElementById('entities');entities.innerHTML='';for(const [id,state] of Object.entries(data.entities||{})){const el=document.createElement('section');el.className='panel entity';const obs=state.observation||{};const dec=state.decision||{};el.innerHTML=`<h2>${esc(id)}</h2><img src="/frames/${encodeURIComponent(id)}.jpg?t=${Date.now()}" onerror="this.style.display='none'" alt="Latest ${esc(id)} view"><pre>Model: ${esc(dec.model||'—')}\nAction: ${esc(dec.action||'—')}\nConfidence: ${esc(dec.confidence??'—')}\nVisible objects: ${esc((obs.visible_objects||[]).map(o=>o.object_type).join(', ')||'—')}\nPosition: ${esc(JSON.stringify(obs.agent?.position||{}))}\nSelf model: ${esc(dec.self_model_summary||'—')}\nUncertainty: ${esc(dec.uncertainty_source||'—')}\nTokens: ${esc(dec.tokens_used??0)}</pre>`;entities.appendChild(el)}
document.getElementById('events').innerHTML=(data.events||[]).map(e=>`<tr><td>${e.sequence}</td><td>${e.tick}</td><td>${esc(e.entity_id||'world')}</td><td>${esc(e.event_type)}</td><td>${esc(detail(e))}</td><td>${new Date(e.created_at).toLocaleTimeString()}</td></tr>`).join('')
}catch(e){document.getElementById('status').innerHTML='<span class="bad">offline</span>'}}
refresh();setInterval(refresh,2000);
</script></body></html>"""


def _status(ledger: EventLedger) -> dict:
    run = ledger.latest_run()
    if run is None:
        return {"run": None, "events": [], "entities": {}, "audit_valid": True}
    events = ledger.events(run["run_id"], limit=100)
    entities: dict[str, dict] = {}
    for event in events:
        entity_id = event.get("entity_id")
        if not entity_id:
            continue
        state = entities.setdefault(entity_id, {})
        if event["event_type"] == "observation" and "observation" not in state:
            state["observation"] = event["payload"]
        if event["event_type"] == "decision" and "decision" not in state:
            state["decision"] = event["payload"]
    return {
        "run": run,
        "events": events,
        "entities": entities,
        "metrics": ledger.metrics(run["run_id"]),
        "audit_valid": ledger.verify(run["run_id"]),
    }


def serve_dashboard(run_dir: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    if host != "localhost" and not ipaddress.ip_address(host).is_loopback:
        raise ValueError("Monitor has no authentication and may bind only to a loopback address. Use an SSH tunnel.")
    ledger = EventLedger(run_dir)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send(HTTPStatus.OK, DASHBOARD_HTML.encode("utf-8"), "text/html; charset=utf-8")
                return
            if parsed.path == "/api/status":
                body = json.dumps(_status(ledger), ensure_ascii=False).encode("utf-8")
                self._send(HTTPStatus.OK, body, "application/json")
                return
            if parsed.path.startswith("/frames/"):
                name = Path(parsed.path).name
                path = ledger.frames_dir / name
                if path.exists() and path.resolve().parent == ledger.frames_dir.resolve():
                    self._send(HTTPStatus.OK, path.read_bytes(), mimetypes.guess_type(path)[0] or "image/jpeg")
                    return
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

        def do_POST(self) -> None:
            command = self.path.removeprefix("/api/control/")
            if command not in {"run", "pause", "stop"}:
                self._send(HTTPStatus.BAD_REQUEST, b"invalid command", "text/plain")
                return
            ledger.write_control(command)
            self._send(HTTPStatus.OK, json.dumps({"command": command}).encode(), "application/json")

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"AEON monitor: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
