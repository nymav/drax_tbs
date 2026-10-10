"""Reproducible local retrieval benchmark; never sends documents to a model API."""

import argparse
import json
import tempfile
import time
import tracemalloc
from pathlib import Path
from app import config
from app.services import store


def evaluate(neural=False):
    dataset = json.loads((Path(__file__).resolve().parents[1] / "benchmarks/retrieval.json").read_text())
    original = config.DATA_DIR, config.DB_PATH, config.UPLOAD_DIR
    results = {}
    with tempfile.TemporaryDirectory() as temp:
        config.DATA_DIR = Path(temp)
        config.DB_PATH = Path(temp) / "workspace.sqlite3"
        config.UPLOAD_DIR = Path(temp) / "pdfs"
        config.UPLOAD_DIR.mkdir()
        identity = "00000000-0000-4000-8000-000000000099"
        (config.UPLOAD_DIR / f"{identity}.pdf").write_bytes(b"benchmark fingerprint only")
        store.add_book(identity, "Original regression corpus", "DRAX", 8)
        vectors = None
        if neural:
            from app.services.embedding import get_embeddings

            vectors = get_embeddings([p["text"] for p in dataset["passages"]])
        store.replace_passages(identity, dataset["passages"], vectors)
        from app.services.vector_store import hybrid_search

        methods = {"lexical": store.search}
        if neural:
            methods["hybrid_reranked"] = hybrid_search
        try:
            for name, search in methods.items():
                queries = dataset["queries"] if neural else [q for q in dataset["queries"] if not q.get("semantic")]
                recalls, reciprocal, latencies = [], [], []
                tracemalloc.start()
                for query in queries:
                    start = time.perf_counter()
                    ranked = search(identity, query["query"], limit=3)
                    latencies.append((time.perf_counter() - start) * 1000)
                    pages = [p["page"] for p in ranked]
                    recalls.append(len(set(pages) & set(query["relevant"])) / len(query["relevant"]))
                    reciprocal.append(
                        next((1 / rank for rank, page in enumerate(pages, 1) if page in query["relevant"]), 0)
                    )
                memory = tracemalloc.get_traced_memory()[1]
                tracemalloc.stop()
                # Neural similarity requires a calibrated no-match threshold; report, do not silently gate it.
                abstention = sum(not search(identity, q, limit=3) for q in dataset["abstentions"]) / len(
                    dataset["abstentions"]
                )
                results[name] = {
                    "queries": len(queries),
                    "recall_at_3": sum(recalls) / len(recalls),
                    "mrr": sum(reciprocal) / len(reciprocal),
                    "abstention": abstention,
                    "p95_ms": sorted(latencies)[int(0.95 * (len(latencies) - 1))],
                    "python_peak_bytes": memory,
                }
        finally:
            config.DATA_DIR, config.DB_PATH, config.UPLOAD_DIR = original
    return results, dataset["lexical_gate"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--neural", action="store_true")
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    results, gates = evaluate(args.neural)
    rendered = json.dumps(results, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n")
    if args.gate:
        if args.neural:
            neural, lexical = results["hybrid_reranked"], results["lexical"]
            if any(neural[key] < max(lexical[key], threshold) for key, threshold in gates.items()):
                raise SystemExit("Hybrid retrieval regression gate failed")
        elif any(results["lexical"][key] < threshold for key, threshold in gates.items()):
            raise SystemExit("Retrieval regression gate failed")
