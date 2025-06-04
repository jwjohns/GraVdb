# build_embeddings.py
import json
import pickle
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy import sparse

# -------------- Load all_chunks.json --------------
with open("all_chunks.json", "r", encoding="utf-8") as f:
    all_chunks = json.load(f)

texts = [c["text"] for c in all_chunks]
chunk_ids = [c["chunk_id"] for c in all_chunks]

# -------------- Fit TF-IDF as a sparse matrix --------------
vectorizer = TfidfVectorizer(max_df=0.85, min_df=2)  
# max_df/min_df help prune extremely rare or extremely common terms.
tfidf_sparse = vectorizer.fit_transform(texts)  
# tfidf_sparse shape: (N_chunks, N_features) but stored as sparse

# -------------- Persist vectorizer and sparse matrix --------------
with open("vectorizer.pkl", "wb") as f:
    pickle.dump(vectorizer, f)

sparse.save_npz("chunk_embeddings_sparse.npz", tfidf_sparse)

# -------------- Persist chunk_ids --------------
with open("chunk_ids.json", "w", encoding="utf-8") as f:
    json.dump(chunk_ids, f)

print("Wrote vectorizer.pkl, chunk_embeddings_sparse.npz, chunk_ids.json")

