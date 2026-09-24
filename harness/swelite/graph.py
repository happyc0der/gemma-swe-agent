"""Code-intelligence graph tools backing get_code_neighbors / search_similar_code / get_code_subgraph."""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import numpy as np


class CodeGraph:
    def __init__(self, graph_path: Path | None, embeddings_path: Path | None):
        self.g = nx.MultiDiGraph()
        self.emb: dict[str, np.ndarray] = {}
        self.available = False
        if graph_path is not None:
            self._load_graph(graph_path)
        if embeddings_path is not None:
            self._load_embeddings(embeddings_path)
        self.available = self.g.number_of_nodes() > 0
        self._lower = {n.lower(): n for n in self.g.nodes}

    def _load_graph(self, path: Path) -> None:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        for n in d.get("nodes", []):
            nid = n.get("id")
            if nid is None:
                continue
            self.g.add_node(nid, name=n.get("name", nid), text=n.get("text", ""))
        for e in d.get("edges", d.get("links", [])):
            s, t = e.get("source"), e.get("target")
            if s is None or t is None:
                continue
            self.g.add_edge(s, t, key=e.get("key", 0), type=e.get("type", "calls"))

    def _load_embeddings(self, path: Path) -> None:
        with np.load(path) as z:
            for k in z.files:
                self.emb[k] = np.asarray(z[k], dtype=np.float32).ravel()
        if not self.g.number_of_nodes():
            for k in self.emb:
                self.g.add_node(k, name=k, text="")

    # 4-tier symbol resolution (README 6.3)
    def resolve(self, name: str) -> str | None:
        if not name:
            return None
        if name in self.g:
            return name
        cands = [n for n in self.g.nodes if n.endswith("." + name) or n.endswith("/" + name)]
        if len(cands) >= 1:
            return sorted(cands, key=len)[0]
        low = name.lower()
        if low in self._lower:
            return self._lower[low]
        cands = [n for n in self.g.nodes if low in n.lower()]
        if cands:
            return sorted(cands, key=len)[0]
        return None

    def neighbors(self, node: str, edge_type: str | None = None, max_neighbors: int = 50) -> dict:
        r = self.resolve(node)
        if r is None:
            return {"status": "error", "error_type": "NodeNotFound", "error_message": f"symbol not found: {node}"}
        out: list[str] = []
        et = edge_type.lower() if edge_type else None
        for _, t, d in self.g.out_edges(r, data=True):
            if et and str(d.get("type", "")).lower() != et:
                continue
            out.append(f"{r} -[{d.get('type')}]-> {t}")
        for s, _, d in self.g.in_edges(r, data=True):
            if et and str(d.get("type", "")).lower() != et:
                continue
            out.append(f"{s} -[{d.get('type')}]-> {r}")
        seen: list[str] = []
        for x in out:
            if x not in seen:
                seen.append(x)
        return {"status": "ok", "node": r, "neighbors": seen[:max_neighbors], "count": len(seen)}

    def similar(self, query: str, k: int = 10) -> dict:
        r = self.resolve(query)
        if r is None or r not in self.emb:
            # fall back to any embedding key that resolves by suffix/substring
            low = query.lower()
            keys = [x for x in self.emb if x.endswith("." + query) or low in x.lower()]
            r = sorted(keys, key=len)[0] if keys else None
        if r is None:
            return {"status": "error", "error_type": "NodeNotFound", "error_message": f"query did not resolve to a known symbol: {query}. Pass a class/function/module name."}
        q = self.emb[r]
        names = [n for n in self.emb if n != r]
        if not names:
            return {"status": "ok", "query": r, "results": [], "count": 0}
        M = np.stack([self.emb[n] for n in names])
        sims = M @ q / (np.linalg.norm(M, axis=1) * np.linalg.norm(q) + 1e-9)
        idx = np.argsort(-sims)[:k]
        results = []
        for i in idx:
            n = names[i]
            code = self.g.nodes[n].get("text", "") if n in self.g else ""
            results.append({"node_name": n, "code": code[:1500], "similarity": round(float(sims[i]), 4)})
        return {"status": "ok", "query": r, "results": results, "count": len(results)}

    def subgraph(self, nodes: list[str]) -> dict:
        resolved = [x for x in (self.resolve(n) for n in nodes) if x]
        sg = self.g.subgraph(resolved)
        edges = [{"from": s, "to": t, "type": d.get("type")} for s, t, d in sg.edges(data=True)]
        return {"status": "ok", "nodes": list(sg.nodes), "edges": edges, "node_count": sg.number_of_nodes(), "edge_count": len(edges)}
