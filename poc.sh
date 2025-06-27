# (1) Extract JSON + images from PDF:
python extract_json.py

# (2) Build chunk metadata from per-page JSONs:
python build_chunks.py

# (3) Compute and persist embeddings:
python build_embeddings.py

# (4) Build and persist the graph:
python build_graph.py

# (5) Start the query service:
python serve_hybrid.py

