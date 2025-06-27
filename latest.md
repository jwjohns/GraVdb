The root cause of those errors is that a vanilla TF–IDF on \~27 000 “chunks” (one per page) produces hundreds of thousands of features. Converting that huge sparse matrix (`27194 × ~156 316`) into a dense NumPy array blows past RAM and disk‐write limits. In other words, you cannot hold or save a `(27194, 156316)` float64 array as a dense `chunk_embeddings.npy`.

Below is a revised pipeline that:

1. **Keeps TF–IDF sparse**, or
2. **Applies dimensionality‐reduction** to collapse TF–IDF into a small, dense embedding (e.g. 512 dims) that is easy to store.

I’ll show you both approaches. Choose whichever is more comfortable:

* **Option A (Sparse TF–IDF + On‐the‐Fly Cosine)**:
  Keep `tfidf_matrix` as a SciPy sparse matrix and save it with `save_npz()`. At query time, compute cosine‐similarities in sparse form. This avoids ever densifying the full matrix.

* **Option B (TF–IDF + TruncatedSVD → Dense 512‐Dim)**:
  After fitting TF–IDF, run a TruncatedSVD to reduce each chunk’s feature vector to, say, 512 dimensions. Saving a `27194 × 512` float64 array is \~110 MB, which is reasonable. You then store those 512‐dim vectors in `chunk_embeddings.npy` as before.

Both options let you build the graph exactly as before—but with a manageable embedding representation.

---

## Revised Step 3: Build & Persist Embeddings

Below are **two variants** of `build_embeddings.py`. Use only one.

---

### Option A: Keep TF–IDF Sparse (no dense array)

1. Install `scipy` so you can serialize sparse matrices:

   ```bash
   pip install scipy
   ```

2. Save `build_embeddings_sparse.py`:

   ```python
   # build_embeddings_sparse.py

   import json
   import pickle
   from pathlib import Path
   from sklearn.feature_extraction.text import TfidfVectorizer
   from scipy import sparse

   # -------------- Load all_chunks.json --------------
   with open("all_chunks.json", "r", encoding="utf-8") as f:
       all_chunks = json.load(f)

   texts     = [c["text"]      for c in all_chunks]
   chunk_ids = [c["chunk_id"]  for c in all_chunks]

   # -------------- Fit TF-IDF as a sparse matrix --------------
   vectorizer = TfidfVectorizer(max_df=0.85, min_df=2)  
   # max_df/min_df help prune extremely rare or extremely common terms.
   tfidf_sparse = vectorizer.fit_transform(texts)  
   # tfidf_sparse shape: (27194, #features) but stored as sparse

   # -------------- Persist vectorizer and sparse matrix --------------
   with open("vectorizer.pkl", "wb") as f:
       pickle.dump(vectorizer, f)

   sparse.save_npz("chunk_embeddings_sparse.npz", tfidf_sparse)

   # -------------- Persist chunk_ids --------------
   with open("chunk_ids.json", "w", encoding="utf-8") as f:
       json.dump(chunk_ids, f)

   print("Wrote vectorizer.pkl, chunk_embeddings_sparse.npz, chunk_ids.json")
   ```

3. Run:

   ```bash
   pip install scipy
   python build_embeddings_sparse.py
   ```

   This creates:

   ```
   vectorizer.pkl
   chunk_embeddings_sparse.npz   # a compressed SciPy CSR matrix of shape (27194, ~80 000)
   chunk_ids.json                # list of 27194 chunk IDs
   ```

4. In your service (`serve_hybrid.py`), you will replace the dense‐cosine code with a sparse version. See the “serve” section below.

---

### Option B: TF–IDF + TruncatedSVD → Dense \~512-dim Embeddings

1. Install `scikit‐learn` and `numpy` if not already:

   ```bash
   pip install numpy scikit-learn
   ```

2. Save `build_embeddings_reduced.py`:

   ```python
   # build_embeddings_reduced.py

   import json
   import pickle
   import numpy as np
   from sklearn.feature_extraction.text import TfidfVectorizer
   from sklearn.decomposition import TruncatedSVD
   from pathlib import Path

   # -------------- Load all_chunks.json --------------
   with open("all_chunks.json", "r", encoding="utf-8") as f:
       all_chunks = json.load(f)

   texts     = [c["text"]      for c in all_chunks]
   chunk_ids = [c["chunk_id"]  for c in all_chunks]

   # -------------- Fit TF-IDF (sparse) --------------
   vectorizer = TfidfVectorizer(max_df=0.85, min_df=2)
   tfidf_sparse = vectorizer.fit_transform(texts)  
   # shape: (27194, ~80k features) in sparse form

   # -------------- Reduce Dimensionality with TruncatedSVD --------------
   # We choose 512 components (you can choose 256, 768, etc. as needed)
   n_components = 512
   svd = TruncatedSVD(n_components=n_components, n_iter=10, random_state=42)
   reduced_embeddings = svd.fit_transform(tfidf_sparse)  
   # shape: (27194, 512). This is dense.

   # -------------- Persist vectorizer, the SVD model, and reduced embeddings --------------
   # We need vectorizer + SVD to transform any future query.
   with open("vectorizer.pkl", "wb") as f:
       pickle.dump(vectorizer, f)
   with open("svd_model.pkl", "wb") as f:
       pickle.dump(svd, f)

   # Save reduced embeddings as a dense NumPy array
   np.save("chunk_embeddings.npy", reduced_embeddings.astype(np.float32))

   # -------------- Persist chunk_ids --------------
   with open("chunk_ids.json", "w", encoding="utf-8") as f:
       json.dump(chunk_ids, f)

   print(f"Wrote vectorizer.pkl, svd_model.pkl, and chunk_embeddings.npy (shape {reduced_embeddings.shape})")
   ```

3. Run:

   ```bash
   python build_embeddings_reduced.py
   ```

   This creates:

   ```
   vectorizer.pkl       # to vectorize any query
   svd_model.pkl        # to reduce a query vector to 512 dims
   chunk_embeddings.npy # shape (27194, 512) float32
   chunk_ids.json       # list of 27194 chunk IDs
   ```

---

## Revised Graph Build (Step 4)

Below is **`build_graph.py`** (unchanged except that it now expects `chunk_embeddings.npy` if you chose Option B, or it ignores embeddings if you chose Option A):

```python
# build_graph.py
import json
import pickle
import numpy as np
import networkx as nx

# 1) Load all_chunks.json
with open("all_chunks.json", "r", encoding="utf-8") as f:
    all_chunks = json.load(f)

# 2) Load the embeddings
# If you used Option B (TruncatedSVD → NumPy), uncomment:
embeddings = np.load("chunk_embeddings.npy")  # shape: (27194, 512)

# If you used Option A (sparse), just skip loading embeddings here. 
# You could load the sparse matrix on-the-fly in serve_hybrid.

# 3) Build sets of unique sections, signals, eco tables
sections = {c["section_id"] for c in all_chunks}
signals  = {sig for c in all_chunks for sig in c["signal_ids"]}
ecos     = {eco for c in all_chunks for eco in c["eco_ids"]}

# 4) Create the graph
G = nx.Graph()

# 4a) Add Section, Signal, ECO nodes
for sec in sections:
    G.add_node(sec, type="Section")
for sig in signals:
    G.add_node(sig, type="SystemSignal")
for eco in ecos:
    G.add_node(eco, type="ECO_Table")

# 4b) Add Chunk nodes (including embedding & image_paths)
for idx, chunk in enumerate(all_chunks):
    cid    = chunk["chunk_id"]

    # Attach either dense embedding (512 dims) or leave out
    G.add_node(
        cid,
        type="Chunk",
        text=chunk["text"],
        section_id=chunk["section_id"],
        signal_ids=chunk["signal_ids"],
        eco_ids=chunk["eco_ids"],
        image_paths=chunk["image_paths"],
        embedding=embeddings[idx]  # only if Option B
    )

    # Connect chunk → section
    G.add_edge(cid, chunk["section_id"], type="HAS_CHUNK")

    # Connect chunk → each SystemSignal
    for sig in chunk["signal_ids"]:
        G.add_edge(cid, sig, type="CONTAINS_SIGNAL")

    # Connect chunk → each ECO
    for eco in chunk["eco_ids"]:
        G.add_edge(cid, eco, type="REFERS_TO_ECO")

# 5) Serialize graph
with open("graph.pkl", "wb") as f:
    pickle.dump(G, f)

print("Wrote graph.pkl")
```

> **Run:**
>
> ```bash
> pip install networkx
> python build_graph.py
> ```

**File produced:**

```
graph.pkl   # Contains all nodes, edges, + node attribute "embedding" if Option B
```

---

## Revised Service Code (Step 5)

Now we write two slight variants of `serve_hybrid.py`—one for **Option A** (sparse TF–IDF) and one for **Option B** (reduced 512-dim).

---

### 5A. `serve_hybrid_sparse.py` (using sparse TF–IDF)

```python
#!/usr/bin/env python3
"""
serve_hybrid_sparse.py

Uses a sparse TF-IDF matrix to compute cosine similarity on-the-fly
and a NetworkX graph for neighbor lookups.

1) Loads graph.pkl (NetworkX) 
2) Loads vectorizer.pkl (TF-IDF) 
3) Loads chunk_embeddings_sparse.npz (SciPy CSR)
4) Loads chunk_ids.json 

Then exposes: 
  - semantic_search(query, top_n) 
  - hybrid_search(query, top_n)
"""

import pickle
import json
import numpy as np
import networkx as nx
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity

# 1) Load persisted objects
with open("graph.pkl", "rb") as f:
    G = pickle.load(f)

with open("vectorizer.pkl", "rb") as f:
    vectorizer = pickle.load(f)

# Load the sparse TF-IDF matrix
tfidf_sparse = sparse.load_npz("chunk_embeddings_sparse.npz")  # shape (27194, ~80k)

with open("chunk_ids.json", "r", encoding="utf-8") as f:
    chunk_ids = json.load(f)  # 27194 strings

# 2) Build chunk_id → index map
chunk_to_index = {cid: idx for idx, cid in enumerate(chunk_ids)}

# 3) Semantic search (sparse cosines)
def semantic_search(query: str, top_n: int = 5):
    """
    1) Transform query → sparse TF-IDF vector (1 × #features)
    2) Compute cosine similarity between that row and tfidf_sparse (27194 × #features)
    3) Return top_n matching chunk_ids with metadata
    """
    q_vec = vectorizer.transform([query])  # sparse shape (1, #features)

    # Compute cosine similarity: we can do:
    #   sim = (q_vec · tfidf_sparse.T) / (||q_vec|| * ||each row||)
    # Using sklearn’s helper:
    sims = cosine_similarity(q_vec, tfidf_sparse)[0]  # dense array shape (27194,)

    ranked_indices = sims.argsort()[::-1][:top_n]
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
        })
    return results

# 4) Hybrid search: same as before, but calls semantic_search
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

# 5) Simple CLI
if __name__ == "__main__":
    print("Hybrid‐sparse search service loaded. Type a query, or 'quit'.")
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
```

> **Run:**
>
> ```bash
> pip install scipy networkx scikit-learn
> python serve_hybrid_sparse.py
> ```

---

### 5B. `serve_hybrid_reduced.py` (using 512-dim dense embeddings)

```python
#!/usr/bin/env python3
"""
serve_hybrid_reduced.py

Uses 512-dim dense embeddings (TF-IDF → TruncatedSVD) to compute cosine similarity
and a NetworkX graph to fetch neighbors.

1) Load graph.pkl (NetworkX includes chunk embedding as node attribute)
2) Load vectorizer.pkl (TF-IDF)
3) Load svd_model.pkl  (TruncatedSVD to reduce query to 512 dims)
4) Load chunk_embeddings.npy (shape: (27194, 512))
5) Load chunk_ids.json

Exposes:
  - semantic_search(query, top_n)
  - hybrid_search(query, top_n)
"""

import pickle
import json
import numpy as np
import networkx as nx
from sklearn.metrics.pairwise import cosine_similarity

# 1) Load persisted graph
with open("graph.pkl", "rb") as f:
    G = pickle.load(f)

# 2) Load TF-IDF vectorizer & SVD model
with open("vectorizer.pkl", "rb") as f:
    vectorizer = pickle.load(f)
with open("svd_model.pkl", "rb") as f:
    svd_model = pickle.load(f)

# 3) Load reduced embeddings and chunk_ids
chunk_embeddings = np.load("chunk_embeddings.npy")  # (27194, 512)
with open("chunk_ids.json", "r", encoding="utf-8") as f:
    chunk_ids = json.load(f)  # 27194 strings

# 4) Build map chunk_id → index
chunk_to_index = {cid: idx for idx, cid in enumerate(chunk_ids)}

# 5) Semantic search (dense cosine)
def semantic_search(query: str, top_n: int = 5):
    """
    1) vectorizer.transform → sparse (1 × #features)
    2) svd_model.transform → (1 × 512) dense
    3) cosine_similarity against chunk_embeddings (27194 × 512)
    """
    tfidf_q = vectorizer.transform([query])        # sparse (1, #features)
    q_vec   = svd_model.transform(tfidf_q)         # dense (1, 512)
    sims    = cosine_similarity(q_vec, chunk_embeddings)[0]  # (27194,)
    ranked_idxs = sims.argsort()[::-1][:top_n]

    results = []
    for idx in ranked_idxs:
        cid  = chunk_ids[idx]
        node = G.nodes[cid]
        results.append({
            "chunk_id": cid,
            "score": float(sims[idx]),
            "text": node["text"],
            "section_id": node["section_id"],
            "signal_ids": node["signal_ids"],
            "eco_ids": node["eco_ids"],
            "image_paths": node["image_paths"],
        })
    return results

# 6) Hybrid search
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

# 7) Simple CLI
if __name__ == "__main__":
    print("Hybrid-reduced search service started. Type a query (or 'quit').")
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
```

> **Run:**
>
> ```bash
> pip install networkx numpy scikit-learn
> python serve_hybrid_reduced.py
> ```

---

## 7. Putting It All Together

Below is a final “playbook”:

1. **Extract JSON + images**

   ```bash
   python extract_json.py
   ```

2. **Build chunk metadata (including flowchart image paths)**

   ```bash
   python build_chunks.py
   ```

3. **Build embeddings**

   * **If you want to keep a sparse TF–IDF**:

     ```bash
     python build_embeddings_sparse.py
     # → produces vectorizer.pkl, chunk_embeddings_sparse.npz, chunk_ids.json
     ```
   * **If you want 512-dim dense vectors**:

     ```bash
     python build_embeddings_reduced.py
     # → produces vectorizer.pkl, svd_model.pkl, chunk_embeddings.npy, chunk_ids.json
     ```

4. **Build the graph**

   ```bash
   python build_graph.py
   # → produces graph.pkl
   ```

5. **Serve queries**

   * **For sparse TF–IDF path**:

     ```bash
     python serve_hybrid_sparse.py
     ```
   * **For 512-dim reduced path**:

     ```bash
     python serve_hybrid_reduced.py
     ```

At that point, your CLI will accept queries like:

```
> clear service indicator
Top 5 results for 'clear service indicator':
  • chunk_id: ch_00005, score: 0.312
    text: Service reset function: clear maintenance flag …
    section_id: 12.17.1.5
    signal_ids: ['LV_ER_BAL_HOM_REQ']
    eco_ids: ['ECO-0105']
    image_paths: ['data/pdf_extracted/images/page_00005_img_52.png']
    section_neighbors: ['12.17.1.5']
    signal_neighbors: ['LV_ER_BAL_HOM_REQ']
    eco_neighbors: ['ECO-0105']
  …
```

Because each chunk’s `"image_paths"` now lists the actual PNG flowchart(s), you can immediately load or display those images in whatever front‐end you build.

---

## Summary of Required Files

After you follow these steps, your directory should contain:

```
Funktionsrahmen-Simos-18.1.pdf

data/pdf_extracted/
  page_00001.json
  …
  page_27194.json
  images/
    page_00001_img_23.png
    …

build_chunks.py
build_embeddings_sparse.py    # or build_embeddings_reduced.py, not both
build_graph.py

# Outputs from build_embeddings:
vectorizer.pkl
# If sparse path:
chunk_embeddings_sparse.npz
# If reduced path:
svd_model.pkl
chunk_embeddings.npy

chunk_ids.json
graph.pkl

serve_hybrid_sparse.py     # if you used the sparse‐TFIDF path
# ––or––
serve_hybrid_reduced.py    # if you used the TruncatedSVD → dense path
```

You should now be able to run:

```bash
python extract_json.py
python build_chunks.py
python build_embeddings_<sparse|reduced>.py
python build_graph.py
python serve_hybrid_<sparse|reduced>.py
```

…and have a working “one‐process” hybrid search that:

* Identifies each flowchart image on every page (via `"image_paths"`)
* Indexes all text in a sparse or reduced‐dense embedding
* Quickly returns top‐N chunks for any query, plus each chunk’s Section, SystemSignal, ECO, and associated PNG flowchart(s).
