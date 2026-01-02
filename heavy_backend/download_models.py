# heavy_backend/download_models.py
from sentence_transformers import SentenceTransformer
import os

MODEL_DIR = os.environ.get("MODEL_CACHE_DIR", "/opt/models")
os.makedirs(MODEL_DIR, exist_ok=True)

models = [
    "sentence-transformers/all-MiniLM-L6-v2",
    # add more if needed
]

for m in models:
    print("Downloading", m)
    SentenceTransformer(m, cache_folder=MODEL_DIR)
    print("Done", m)
