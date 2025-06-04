
# build_chunks.py
import json
import re
from pathlib import Path

INPUT_DIR = Path("data/pdf_extracted")
OUTPUT_CHUNKS = Path("all_chunks.json")

chunk_list = []

# Regex patterns
section_pattern = re.compile(r"^(\d+\.\d+(\.\d+)*)")  # e.g. “12.17.1.4”
signal_pattern = re.compile(r"([A-Z0-9_]{5,})")       # crude capture of uppercase IDs
eco_pattern = re.compile(r"ECO[- ]?(\d{3,4})", re.IGNORECASE)

for page_file in sorted(INPUT_DIR.glob("page_*.json")):
    data = json.loads(page_file.read_text(encoding="utf-8"))
    page_num = data["page_number"]

    # 1) Determine section_id by scanning the first few text blocks for a heading
    section_id = None
    for block in data["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"])
            m = section_pattern.match(text.strip())
            if m:
                section_id = m.group(1)
                break
        if section_id:
            break
    if not section_id:
        section_id = "UNKNOWN_SECTION"

    # 2) Collect all signals & eco IDs on this page
    text_all = " ".join(
        span["text"] for block in data["blocks"] for line in block["lines"] for span in line["spans"]
    )
    signal_ids = list({s for s in signal_pattern.findall(text_all) if not s.isdigit()})
    eco_ids = [f"ECO-{m.group(1)}" for m in eco_pattern.finditer(text_all)]

    # 3) All images on this page (we stored them in page JSON)
    image_paths = [img["image_path"] for img in data["images"]]

    # 4) Build a chunk record
    chunk_id = f"ch_{page_num:05d}"
    chunk_list.append({
        "chunk_id": chunk_id,
        "text": text_all,
        "section_id": section_id,
        "signal_ids": signal_ids,
        "eco_ids": eco_ids,
        "image_paths": image_paths,
    })

# 5) Write to disk
with open(OUTPUT_CHUNKS, "w", encoding="utf-8") as f:
    json.dump(chunk_list, f, indent=2)

print(f"Wrote {len(chunk_list)} chunks to {OUTPUT_CHUNKS}")

