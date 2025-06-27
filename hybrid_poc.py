import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 1) Expanded sample chunks with more varied, slightly noisy phrasing
chunks = [
    {
        "chunk_id": "ch_0001",
        "text": "Initialization at reset: LV_ER_BAL_HOM_REQ = 0. Default oil change flag reset.",
        "section_id": "12.17.1.4",
        "signal_ids": ["LV_ER_BAL_HOM_REQ"],
        "eco_ids": ["ECO-0105"]
    },
    {
        "chunk_id": "ch_0002",
        "text": "Cold start enrichment: ignition.advance is retarded by 5° when coolant temperature is under 20°C.",
        "section_id": "64.5.3",
        "signal_ids": ["IGNITION_ADVANCE"],
        "eco_ids": ["ECO-0202"]
    },
    {
        "chunk_id": "ch_0003",
        "text": "Oil change service indicator engages after 10000 km; LV_OIL_CHG_CAN toggles the dash warning.",
        "section_id": "52.81.3.3.1.4.2",
        "signal_ids": ["LV_OIL_CHG_CAN"],
        "eco_ids": ["ECO-0105", "ECO-0842"]
    },
    {
        "chunk_id": "ch_0004",
        "text": "Fuel trim table reference: AFR_TARGET = 14.7:1; adjustments made via fuel.trim calibration maps.",
        "section_id": "37.2.1",
        "signal_ids": ["AFR_TARGET", "FUEL_TRIM"],
        "eco_ids": ["ECO-0303"]
    },
    {
        "chunk_id": "ch_0005",
        "text": "Service reset function: clear maintenance flag when LV_ER_BAL_HOM_REQ sets to 0 and notify driver.",
        "section_id": "12.17.1.5",
        "signal_ids": ["LV_ER_BAL_HOM_REQ"],
        "eco_ids": ["ECO-0105"]
    },
    {
        "chunk_id": "ch_0006",
        "text": "During cold engine start, enrich fuel: ignition timing retarded, AF correction applied using cold_engine_fuel_map.",
        "section_id": "64.5.4",
        "signal_ids": ["IGNITION_ADVANCE", "AFR_TARGET"],
        "eco_ids": ["ECO-0202", "ECO-0303"]
    },
    {
        "chunk_id": "ch_0007",
        "text": "Setting LV_OIL_CHG_CAN = 1 triggers oil change reminder; resets only when service complete and reset tool used.",
        "section_id": "52.81.3.3.1.4.3",
        "signal_ids": ["LV_OIL_CHG_CAN"],
        "eco_ids": ["ECO-0842"]
    },
    {
        "chunk_id": "ch_0008",
        "text": "Boost control map: overboost prevention kicks in at 1.2 bar; BOOST_LIMIT signal monitored every 10 ms.",
        "section_id": "68.4.2",
        "signal_ids": ["BOOST_LIMIT"],
        "eco_ids": ["ECO-0505"]
    },
    {
        "chunk_id": "ch_0009",
        "text": "Miscalibration: afr.target drift observed; fuel mapping requires recalibration using table fuel_correction_map in ECO-0303.",
        "section_id": "37.2.2",
        "signal_ids": ["AFR_TARGET"],
        "eco_ids": ["ECO-0303"]
    },
    {
        "chunk_id": "ch_0010",
        "text": "Ignition map: under low RPM, IGNITION_ADVANCE is set to base_ign_map; adjust if engine load below threshold.",
        "section_id": "64.5.5",
        "signal_ids": ["IGNITION_ADVANCE"],
        "eco_ids": ["ECO-0202"]
    }
]

# 2) Compute TF-IDF embeddings for each chunk
texts = [c["text"] for c in chunks]
vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(texts)

# 3) Build the graph and attach embeddings
G = nx.Graph()

# Add Section nodes
sections = {c["section_id"] for c in chunks}
for sec in sections:
    G.add_node(sec, type="Section")

# Add Chunk nodes with embedding attribute
for idx, c in enumerate(chunks):
    embedding = tfidf_matrix[idx].toarray()[0]
    G.add_node(c["chunk_id"], type="Chunk", text=c["text"], embedding=embedding)
    G.add_edge(c["chunk_id"], c["section_id"], type="HAS_CHUNK")

# Add SystemSignal nodes and link
signals = {sig for c in chunks for sig in c["signal_ids"]}
for sig in signals:
    G.add_node(sig, type="SystemSignal")

for c in chunks:
    for sig in c["signal_ids"]:
        G.add_edge(c["chunk_id"], sig, type="CONTAINS_SIGNAL")
        G.add_edge(sig, c["section_id"], type="DOCUMENTED_IN")

# Add ECO_Table nodes and link
eco_tables = {eco for c in chunks for eco in c["eco_ids"]}
for eco in eco_tables:
    G.add_node(eco, type="ECO_Table")

for c in chunks:
    for eco in c["eco_ids"]:
        G.add_edge(c["chunk_id"], eco, type="REFERS_TO_ECO")

# 4) Semantic search function
def semantic_search(query, top_n=3):
    q_vec = vectorizer.transform([query]).toarray()[0]
    embeddings = np.array([G.nodes[c["chunk_id"]]['embedding'] for c in chunks])
    sims = cosine_similarity([q_vec], embeddings)[0]
    ranked_indices = sims.argsort()[::-1][:top_n]
    results = []
    for idx in ranked_indices:
        c = chunks[idx]
        results.append({
            "chunk_id": c["chunk_id"],
            "score": float(sims[idx]),
            "text": c["text"],
            "section_id": c["section_id"],
            "signal_ids": c["signal_ids"],
            "eco_ids": c["eco_ids"]
        })
    return results

# 5) Hybrid search: combine semantic + graph neighbors
def hybrid_search(query, top_n=3):
    sem_results = semantic_search(query, top_n)
    hybrid_output = []
    for res in sem_results:
        chunk_id = res["chunk_id"]
        neighbors = list(G.neighbors(chunk_id))
        section_neighbors = [n for n in neighbors if G.nodes[n]['type'] == 'Section']
        signal_neighbors = [n for n in neighbors if G.nodes[n]['type'] == 'SystemSignal']
        eco_neighbors = [n for n in neighbors if G.nodes[n]['type'] == 'ECO_Table']
        hybrid_output.append({
            "chunk_id": chunk_id,
            "score": res["score"],
            "text": res["text"],
            "section_neighbors": section_neighbors,
            "signal_neighbors": signal_neighbors,
            "eco_neighbors": eco_neighbors
        })
    return hybrid_output

# 6) Run tests with several queries
queries = [
    "clear service indicator",
    "cold engine start fuel enrichment",
    "adjust AFR target",
    "oil change reminder",
    "boost limit prevention"
]

# Display results
print("=== Hybrid Search Results ===")
for q in queries:
    results = hybrid_search(q, top_n=3)
    print(f"\nQuery: '{q}'")
    for r in results:
        print(f"  - chunk_id: {r['chunk_id']}, score: {r['score']:.3f}")
        print(f"    text: {r['text']}")
        print(f"    section_neighbors: {r['section_neighbors']}")
        print(f"    signal_neighbors: {r['signal_neighbors']}")
        print(f"    eco_neighbors: {r['eco_neighbors']}")

