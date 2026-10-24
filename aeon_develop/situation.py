"""One connected representation of the present: perception, memory, expectation
and intention as nodes that refer to the same ongoing situation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SituationGraph:
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: list[dict[str, str]] = field(default_factory=list)

    def add(self, node_id: str, kind: str, **attrs: Any) -> None:
        self.nodes[node_id] = {"kind": kind, **attrs}

    def link(self, src: str, rel: str, dst: str, why: str = "") -> None:
        self.edges.append({"src": src, "rel": rel, "dst": dst, "why": why})

    def has_edge(self, src: str, rel: str, dst: str | None = None) -> bool:
        return any(e["src"] == src and e["rel"] == rel and (dst is None or e["dst"] == dst) for e in self.edges)

    def edges_from(self, src: str, rel: str) -> list[dict[str, str]]:
        return [e for e in self.edges if e["src"] == src and e["rel"] == rel]

    def intended_object(self) -> str | None:
        for e in self.edges:
            if e["src"] == "intention" and e["rel"] == "targets":
                return e["dst"]
        return None

    def target_estimate(self) -> tuple[float, float] | None:
        target = self.intended_object()
        if target and target in self.nodes and self.nodes[target].get("estimate"):
            est = self.nodes[target]["estimate"]
            return (est[0], est[1])
        return None

    def narrate(self) -> list[str]:
        """Words come last: a template rendering of relations that already drove decisions."""
        out: list[str] = []
        target = self.intended_object()
        if target:
            name = target.split(":", 1)[1]
            parts = [f"That object is the {name}"]
            if self.has_edge("self", "moved", target):
                parts[0] = f"That object is the {name} I moved"
            if self.has_edge(f"prediction:{target}", "contradicted_by"):
                parts.append("its current position contradicts my prediction")
            for e in self.edges_from(target, "uncertain_because"):
                parts.append(f"I am uncertain because {e['dst'].split(':', 1)[1]} was unreliable earlier")
            out.append("; ".join(parts) + ".")
        self_node = self.nodes.get("self", {})
        if self_node.get("delay"):
            out.append(f"My commands take effect {self_node['delay']} ticks late, so I act ahead of time.")
        for e in self.edges_from("self", "extended_by"):
            out.append(f"Signal {e['dst'].split(':', 1)[1]} is part of a tool that extends my reach ({e['why']}).")
        for e in self.edges_from("inquiry", "considers"):
            out.append(f"I am considering: {e['why']}")
        if self_node.get("frozen"):
            out.append("My self-model is frozen: I can notice errors but cannot revise myself.")
        return out

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": self.nodes, "edges": self.edges, "narration": self.narrate()}
