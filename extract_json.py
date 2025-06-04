# extract_json.py
import fitz  # PyMuPDF
from pathlib import Path
import json

PDF_PATH = Path("Funktionsrahmen-Simos-18.1.pdf")
OUTPUT_DIR = Path("data/pdf_extracted")
IMAGE_DIR = OUTPUT_DIR / "images"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

doc = fitz.open(str(PDF_PATH))

for page_idx in range(len(doc)):
    page = doc[page_idx]
    page_dict = page.get_text("dict")

    # 1) Build a map: xref → list of bboxes from type==1 blocks
    image_bbox_map = {}
    clean_blocks = []
    for block in page_dict["blocks"]:
        if block["type"] == 0:
            clean_blocks.append(block)
        elif block["type"] == 1:
            xref = block.get("image")
            if isinstance(xref, int):
                image_bbox_map.setdefault(xref, []).append(block.get("bbox", []))

    # 2) Extract every embedded image (by xref) on this page
    image_entries = []
    pixmap_cache = {}
    for img_info in page.get_images(full=True):
        xref = img_info[0]
        if xref in pixmap_cache:
            continue
        pix = fitz.Pixmap(doc, xref)
        if pix.n > 4:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        fn = f"page_{page_idx+1:05d}_img_{xref}.png"
        out_path = IMAGE_DIR / fn
        pix.save(str(out_path))
        pixmap_cache[xref] = str(out_path)
        pix = None

        bboxes = image_bbox_map.get(xref, [])
        if not bboxes:
            image_entries.append({
                "xref": xref,
                "image_path": str(out_path),
                "bbox": []
            })
        else:
            for bbox in bboxes:
                image_entries.append({
                    "xref": xref,
                    "image_path": str(out_path),
                    "bbox": bbox
                })

    # 3) Write one JSON for this page
    page_json = {
        "page_number": page_idx + 1,
        "blocks": clean_blocks,
        "images": image_entries
    }
    out_json = OUTPUT_DIR / f"page_{page_idx+1:05d}.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(page_json, f, indent=2)

    print(f"Wrote {out_json}")

