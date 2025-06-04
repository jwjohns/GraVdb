#!/usr/bin/env python3
"""
serve_hybrid.py

A self-contained hybrid search service (vector + graph):

  • On startup, it loads:
      - graph.pkl         (NetworkX graph)
      - vectorizer.pkl    (TF-IDF vectorizer)
      - chunk_embeddings_sparse.npz (Sparse TF-IDF matrix)
      - chunk_ids.json

  • Implements:
      - semantic_search(query, top_n)
      - hybrid_search(query, top_n)

  • Offers a simple CLI to test queries; you can wrap this into FastAPI/Flask if desired.
"""

import pickle
import json
import numpy as np
import networkx as nx
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity
import time
from typing import Dict, List

# Add timing stats dictionary
timing_stats = {
    "query_processing": [],
    "similarity_computation": [],
    "filtering": [],
    "result_building": [],
    "total_search": []
}

# 1) Load persisted objects
with open("graph.pkl", "rb") as f:
    G = pickle.load(f)

with open("vectorizer.pkl", "rb") as f:
    vectorizer = pickle.load(f)

# Load the sparse TF-IDF matrix
tfidf_sparse = sparse.load_npz("chunk_embeddings_sparse.npz")  # shape (N_chunks, N_features)

with open("chunk_ids.json", "r", encoding="utf-8") as f:
    chunk_ids = json.load(f)

# 2) Map chunk_id → index in embeddings array
chunk_to_index = {cid: idx for idx, cid in enumerate(chunk_ids)}

# 3) Semantic search: top N chunks by vector similarity
def semantic_search(query: str, top_n: int = 5) -> List[Dict]:
    search_start = time.time()
    
    # 1) Load data if not already loaded
    load_start = time.time()
    global G, tfidf_sparse, chunk_ids, vectorizer
    if 'G' not in globals():
        load_data()
    load_time = time.time() - load_start
    timing_stats["data_loading"] = load_time
    
    # 2) Vectorize query
    vec_start = time.time()
    q_vec = vectorizer.transform([query])
    vec_time = time.time() - vec_start
    timing_stats["query_processing"].append(vec_time)

    # 3) Compute similarities and rank
    sim_start = time.time()
    sims = cosine_similarity(q_vec, tfidf_sparse)[0]
    sim_time = time.time() - sim_start
    timing_stats["similarity_computation"].append(sim_time)

    # Filter and rank results
    filter_start = time.time()
    valid_idxs = np.where(sims > 1e-6)[0]
    valid_sims = sims[valid_idxs]
    
    if len(valid_idxs) == 0:
        ranked_indices = np.array([], dtype=int)
    else:
        sorted_valid = valid_idxs[valid_sims.argsort()[::-1]]
        ranked_indices = sorted_valid[:top_n]
    filter_time = time.time() - filter_start
    timing_stats["filtering"].append(filter_time)

    # Build results
    results_start = time.time()
    results = []
    for idx in ranked_indices:
        cid = chunk_ids[idx]
        node = G.nodes[cid]
        results.append({
            "chunk_id": cid,
            "score": float(sims[idx]),
            "text": node["text"],
            "section_id": node["section_id"],
            "signal_ids": node["signal_ids"],
            "eco_ids": node["eco_ids"],
            "image_paths": node["image_paths"],
            "section_neighbors": list(G.neighbors(cid)),
            "signal_neighbors": node.get("signal_neighbors", []),
            "eco_neighbors": node.get("eco_neighbors", [])
        })
    results_time = time.time() - results_start
    timing_stats["result_building"].append(results_time)

    # Total search time
    total_time = time.time() - search_start
    timing_stats["total_search"].append(total_time)

    return results

def get_timing_stats() -> Dict:
    """Return current timing statistics with averages"""
    stats = {}
    for key, times in timing_stats.items():
        if isinstance(times, list) and times:
            stats[key] = {
                "last": times[-1],
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "count": len(times)
            }
        elif isinstance(times, (int, float)):
            stats[key] = {"value": times}
    return stats

def print_timing_report():
    """Print a formatted timing report"""
    stats = get_timing_stats()
    print("\nSearch System Timing Report")
    print("-" * 50)
    for operation, metrics in stats.items():
        print(f"\n{operation.replace('_', ' ').title()}:")
        if "value" in metrics:
            print(f"  Time: {metrics['value']:.4f}s")
        else:
            print(f"  Last: {metrics['last']:.4f}s")
            print(f"  Avg:  {metrics['avg']:.4f}s")
            print(f"  Min:  {metrics['min']:.4f}s")
            print(f"  Max:  {metrics['max']:.4f}s")
            print(f"  Count: {metrics['count']}")
    print("-" * 50)

# 4) Hybrid search: semantic + graph neighbors
def hybrid_search(query: str, top_n: int = 5):
    sem_results = semantic_search(query, top_n)
    hybrid_out = []
    for entry in sem_results:
        cid = entry["chunk_id"]
        neighbors = list(G.neighbors(cid))

        section_neighbors = [n for n in neighbors if G.nodes[n]["type"] == "Section"]
        signal_neighbors  = [n for n in neighbors if G.nodes[n]["type"] == "SystemSignal"]
        eco_neighbors     = [n for n in neighbors if G.nodes[n]["type"] == "ECO_Table"]

        hybrid_out.append({
            **entry,
            "section_neighbors": section_neighbors,
            "signal_neighbors":  signal_neighbors,
            "eco_neighbors":     eco_neighbors
        })
    return hybrid_out

# 5) Simple CLI to test queries
if __name__ == "__main__":
    print("Hybrid search service ready. Type a query (or 'quit').")
    while True:
        query = input("\n> ").strip()
        if not query or query.lower() in {"quit", "exit"}:
            break

        results = hybrid_search(query, top_n=5)
        print(f"\nTop {len(results)} results for '{query}':")
        for r in results:
            print(f"  • chunk_id: {r['chunk_id']}, score: {r['score']:.3f}")
            print(f"    text: {r['text']}")
            print(f"    section_id: {r['section_id']}")
            print(f"    signal_ids: {r['signal_ids']}")
            print(f"    eco_ids: {r['eco_ids']}")
            print(f"    image_paths: {r['image_paths']}")
            print(f"    section_neighbors: {r['section_neighbors']}")
            print(f"    signal_neighbors: {r['signal_neighbors']}")
            print(f"    eco_neighbors: {r['eco_neighbors']}\n")
        
        # Print timing report after results
        print("\nTiming Statistics:")
        print("-" * 30)
        stats = get_timing_stats()
        for operation, metrics in stats.items():
            print(f"\n{operation.replace('_', ' ').title()}:")
            if "value" in metrics:
                print(f"  Time: {metrics['value']:.4f}s")
            else:
                print(f"  Last: {metrics['last']:.4f}s")
                print(f"  Avg:  {metrics['avg']:.4f}s")

