from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import Task
from .experiment import CONDITIONS, run
from .session import Session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aeon_develop", description="AEON developmental self-model")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("serve", help="live dashboard with sabotage controls")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8770)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--condition", default="intact", choices=list(CONDITIONS))
    p.add_argument("--tps", type=float, default=15.0)
    e = sub.add_parser("experiment", help="pre-registered ablation experiment")
    e.add_argument("--seeds", type=int, default=20)
    e.add_argument("--out", default="artifacts/aeon-develop-ablation")
    e.add_argument("--conditions", nargs="*", choices=list(CONDITIONS))
    d = sub.add_parser("demo", help="headless story: secret delay → diagnosis → catch without new failure")
    d.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    if args.cmd == "serve":
        from .server import serve
        serve(args.host, args.port, args.seed, args.condition, args.tps)
    elif args.cmd == "experiment":
        result = run(Path(args.out), list(range(args.seeds)), args.conditions)
        print((Path(args.out) / "REPORT.md").read_text())
        held = [p for p in result["predictions"] if p["held"] is not None]
        print(json.dumps({"predictions_held": sum(p["held"] for p in held), "of": len(held)}))
    else:
        s = Session(args.seed)
        s.add(Task("fetch"), Task("fetch", before=lambda w: w.set_delay(3)), Task("fetch"), s.catch_task(), s.catch_task())
        s.run_queue()
        for j in s.agent.journal:
            print(f"[t={j['tick']:>5}] {j['text']}")
        print("\nTasks:")
        for t in s.agent.task_log:
            print(f"  {t.kind:6} success={t.success} failed_grips={t.misses} thought={t.thought}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
