"""
prep_photo.py — Prepare a portrait photo for ASCII conversion.

Steps:
  1. Remove background (rembg) → subject isolated on transparent.
  2. Apply CLAHE via OpenCV → local contrast boost (highlights & shadows).
  3. Composite onto pure white → background maps to spaces in ASCII ramp.
  4. Save grayscale output to data/source-prepped.png.

Usage:
    python scripts/prep_photo.py path/to/your-photo.jpg
"""

import sys
import os
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/prep_photo.py <photo_path>")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"Error: file not found: {src}")
        sys.exit(1)

    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "source-prepped.png"

    print(f"[1/4] Loading '{src}' ...")
    from PIL import Image
    import numpy as np
    import cv2

    pil_img = Image.open(src)

    # ── 1. Remove background (try rembg, fall back to Pillow alpha strip) ─────
    try:
        from rembg import remove
        import io as _io
        print("[2/4] Removing background with rembg ...")
        with open(src, "rb") as f:
            raw = f.read()
        img_no_bg = remove(raw)
        pil_rgba = Image.open(_io.BytesIO(img_no_bg)).convert("RGBA")
    except ImportError:
        print("[2/4] rembg not available - using image as-is (alpha or white bg) ...")
        pil_rgba = pil_img.convert("RGBA")

    # ── 2. Composite onto white ───────────────────────────────────────────────
    print("[3/4] Compositing onto white background ...")
    white = Image.new("RGBA", pil_rgba.size, (255, 255, 255, 255))
    white.paste(pil_rgba, mask=pil_rgba.split()[3])
    pil_rgb = white.convert("RGB")

    # ── 3. CLAHE contrast boost ───────────────────────────────────────────────
    print("[3/4] Applying CLAHE contrast boost ...")
    arr = np.array(pil_rgb)
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l_chan = clahe.apply(l_chan)
    lab_enhanced = cv2.merge([l_chan, a_chan, b_chan])
    arr_enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2RGB)

    # ── 4. Save grayscale ────────────────────────────────────────────────────
    gray = cv2.cvtColor(arr_enhanced, cv2.COLOR_RGB2GRAY)
    cv2.imwrite(str(out_path), gray)
    print(f"[4/4] Saved -> {out_path}")

if __name__ == "__main__":
    main()
