# build_graph.py
import json
import pickle
import networkx as nx

# 1) Load data
with open("all_chunks.json", "r", encoding="utf-8") as f:
    all_chunks = json.load(f)

# 2) Prepare sets of unique sections, signals, eco tables
sections = {c["section_id"] for c in all_chunks}
signals  = {sig for c in all_chunks for sig in c["signal_ids"]}
ecos     = {eco for c in all_chunks for eco in c["eco_ids"]}

# 3) Build the graph
G = nx.Graph()

# 3a) Add Section, Signal, ECO_Table nodes
for sec in sections:
    G.add_node(sec, type="Section")
for sig in signals:
    G.add_node(sig, type="SystemSignal")
for eco in ecos:
    G.add_node(eco, type="ECO_Table")

# 3b) Add Chunk nodes with attributes, plus edges
for c in all_chunks:
    cid = c["chunk_id"]

    G.add_node(
        cid,
        type="Chunk",
        text=c["text"],
        section_id=c["section_id"],
        signal_ids=c["signal_ids"],
        eco_ids=c["eco_ids"],
        image_paths=c["image_paths"]
    )

    # Edge: chunk → section
    G.add_edge(cid, c["section_id"], type="HAS_CHUNK")

    # Edge: chunk → each signal
    for sig in c["signal_ids"]:
        G.add_edge(cid, sig, type="CONTAINS_SIGNAL")

    # Edge: chunk → each ECO
    for eco in c["eco_ids"]:
        G.add_edge(cid, eco, type="REFERS_TO_ECO")

# 4) Serialize the entire graph
with open("graph.pkl", "wb") as f:
    pickle.dump(G, f)

print("Wrote graph.pkl (NetworkX graph)")

