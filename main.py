import fitz  # PyMuPDF
from pathlib import Path
import json

# 1) Path to your PDF (in the same folder as this script)
pdf_path = Path("Funktionsrahmen-Simos-18.1.pdf")
if not pdf_path.exists():
    raise FileNotFoundError(f"Cannot find PDF at {pdf_path.resolve()}")

# 2) Where to dump JSON per page
output_dir = Path("data/pdf_extracted")
output_dir.mkdir(parents=True, exist_ok=True)

# 3) Subdirectory for extracted images
image_dir = output_dir / "images"
image_dir.mkdir(parents=True, exist_ok=True)

# Open the PDF
doc = fitz.open(str(pdf_path))

for page_number in range(len(doc)):
    page = doc[page_number]

    # 4) Get all text blocks via get_text("dict")
    page_dict = page.get_text("dict")  # contains "blocks" with type==0 (text) and type==1 (image)
    clean_blocks = []

    # We'll build a map: xref -> bbox, so that when we extract via get_images(),
    # we can assign the same bbox to that saved image.
    image_bbox_map = {}

    # First pass: collect text‐only blocks, and remember bbox of any 'type==1'
    for block in page_dict["blocks"]:
        if block["type"] == 0:
            # Keep the entire text block (lines + spans) verbatim
            clean_blocks.append(block)

        elif block["type"] == 1:
            # A block-type 1 means "an image is drawn here". The key block["image"] is the xref.
            xref = block.get("image")
            if isinstance(xref, int):
                # Record the bounding box for that xref
                image_bbox_map.setdefault(xref, []).append(block.get("bbox", []))
            # We do NOT store raw bytes here—just the bbox. We'll extract and save
            # the actual image below in step #5.
        else:
            # block["type"] might be something else; ignore for now
            continue

    # 5) Extract each image on this page by xref, save to disk, record a JSON entry
    image_entries = []
    pixmap_cache = {}  # to avoid saving duplicates if the same xref appears multiple times

    # page.get_images(full=True) returns a list of tuples:
    #   [(xref, smask, width, height, bpc, colorspace, altcolorspace, name, filter, decodeparms), ...]
    for img_info in page.get_images(full=True):
        xref = img_info[0]
        if xref in pixmap_cache:
            # We already extracted this xref on a previous iteration
            continue

        # Extract the raw image via its xref
        pix = fitz.Pixmap(doc, xref)
        if pix.n > 4:  # if CMYK or RGBA, convert to RGB
            pix = fitz.Pixmap(fitz.csRGB, pix)

        # Build a filename, e.g.: page_00001_img_23.png
        img_filename = f"page_{page_number+1:05d}_img_{xref}.png"
        out_img = image_dir / img_filename
        pix.save(str(out_img))
        pix = None  # free memory

        # Now assign every bbox we saw for this xref (sometimes there might be multiple)
        bboxes = image_bbox_map.get(xref, [])
        for bbox in bboxes:
            image_entries.append({
                "xref": xref,
                "image_path": str(out_img),
                "bbox": bbox,
            })

        # Cache so we don’t re‐extract the same xref multiple times
        pixmap_cache[xref] = str(out_img)

    # 6) Build the final JSON structure for this page:
    page_json = {
        "page_number": page_number + 1,
        "blocks": clean_blocks,    # all text blocks
        "images": image_entries,   # list of { xref, image_path, bbox }
    }

    # 7) Write out page_00001.json, page_00002.json, etc.
    out_path = output_dir / f"page_{page_number+1:05d}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(page_json, f, indent=2)

    print(f"Wrote {out_path}")

