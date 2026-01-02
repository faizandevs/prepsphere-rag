# utils/pdf_to_text_fast_commented.py

"""
Faster PDF -> JSON exporter with page-level OCR fallback and multi-processing.
This script is designed to handle both normal text PDFs and scanned PDFs.

Key Features:
1. Extract text using pdfplumber or PyMuPDF (fast and reliable).
2. Detect pages that are empty or have very little text.
3. Run OCR only on those pages (using pytesseract) to save time.
4. Multi-processing OCR for faster processing of large PDFs (hundreds of pages).
5. Render PDFs to images using PyMuPDF, no Poppler dependency required.
6. Clean headers and footers heuristically.
7. Save debug images of OCR pages (optional, useful for troubleshooting).
8. Skip PDFs that have already been processed to avoid rework.
"""

import os
import json
import re
import hashlib
import argparse
from pathlib import Path
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from PIL import Image, ImageFilter, ImageOps

# -------------------------------------------------------------
# ---------- PDF Text Extractors ----------
# These functions try to get text from a PDF using two methods:
# pdfplumber and PyMuPDF (fitz).
# If both fail, the script will resort to OCR for scanned pages.
# -------------------------------------------------------------

def extract_with_pdfplumber(path):
    """
    Extract text from a PDF using pdfplumber.
    Returns a list of pages, each a dict with page number and text.

    Args:
        path (str): path to the PDF file
    Returns:
        pages (list[dict]): [{'page': 1, 'text': "..."}, ...]
    """
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("pdfplumber not installed")
    
    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            txt = page.extract_text() or ""  # fallback to empty string
            pages.append({"page": i, "text": txt})
    return pages

def extract_with_pymupdf(path):
    """
    Extract text from a PDF using PyMuPDF (fitz).
    Often faster and more reliable than pdfplumber.

    Args:
        path (str): path to PDF
    Returns:
        pages (list[dict]): [{'page': 1, 'text': "..."}, ...]
    """
    try:
        import fitz
    except ImportError:
        raise RuntimeError("pymupdf not installed")
    
    doc = fitz.open(path)
    pages = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        txt = page.get_text("text") or ""
        pages.append({"page": i + 1, "text": txt})
    return pages

# -------------------------------------------------------------
# ---------- OCR Helpers ----------
# Preprocess images for OCR and run OCR in parallel using multi-processing.
# -------------------------------------------------------------

def preprocess_pil_image(img: Image.Image):
    """
    Enhance image for OCR:
    - Convert to grayscale
    - Apply median filter to reduce noise
    - Increase contrast automatically
    
    Args:
        img (PIL.Image): input image
    Returns:
        PIL.Image: preprocessed image
    """
    im = img.convert("L").filter(ImageFilter.MedianFilter(size=3))
    im = ImageOps.autocontrast(im, cutoff=1)
    return im

def ocr_page_worker(args):
    """
    Worker function to OCR a single page (used by multi-processing pool).
    Returns the page number (1-indexed) and OCR'd text.

    Args (tuple):
        idx: page index (0-indexed)
        img_bytes: BytesIO of image
        lang: Tesseract language
        psm: Page segmentation mode
        oem: OCR engine mode
        tesseract_cmd: explicit path to Tesseract executable
        debug_path: optional path to save debug image
    """
    idx, img_bytes, lang, psm, oem, tesseract_cmd, debug_path = args
    from PIL import Image
    import pytesseract

    img = Image.open(img_bytes)
    img = preprocess_pil_image(img)

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = str(tesseract_cmd)
    
    if debug_path:
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(debug_path)

    config = f'--oem {oem} --psm {psm}'
    text = pytesseract.image_to_string(img, lang=lang, config=config) or ""
    return idx + 1, text  # return 1-indexed page

def ocr_pages_parallel(images, pages_to_ocr=None, lang='eng', psm=3, oem=3, tesseract_cmd=None, debug_dir=None):
    """
    Run OCR on multiple pages in parallel using all CPU cores.
    
    Args:
        images (list[PIL.Image]): list of images to OCR
        pages_to_ocr (set[int]): optional set of page numbers to OCR
        lang, psm, oem: Tesseract options
        tesseract_cmd: optional path to tesseract
        debug_dir: optional folder to save debug images
    Returns:
        list[dict]: [{'page': 1, 'text': "..."}, ...]
    """
    from io import BytesIO
    tasks = []

    for i, img in enumerate(images):
        if pages_to_ocr and (i+1) not in pages_to_ocr:
            continue
        buf = BytesIO()
        img.save(buf, format='PNG')
        debug_path = debug_dir / f"page_{i+1:03d}.png" if debug_dir else None
        tasks.append((i, buf, lang, psm, oem, tesseract_cmd, debug_path))
    
    if not tasks:
        return []

    with Pool(cpu_count()) as pool:
        results = pool.map(ocr_page_worker, tasks)

    return [{"page": i, "text": t} for i, t in results]

# -------------------------------------------------------------
# ---------- PDF to Images ----------
# Render PDF pages to images using PyMuPDF (fast)
# -------------------------------------------------------------

def pdf_to_images_fitz(path, dpi=150):
    """
    Convert PDF pages to images for OCR using PyMuPDF (fitz).

    Args:
        path (str): PDF path
        dpi (int): resolution for rendering
    Returns:
        list[PIL.Image]: images of PDF pages
    """
    import fitz
    import io
    doc = fitz.open(path)
    images = []
    zoom = dpi / 72.0  # PDF points are 72 per inch
    mat = fitz.Matrix(zoom, zoom)
    for p in range(doc.page_count):
        pix = doc.load_page(p).get_pixmap(matrix=mat, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)
    return images

# -------------------------------------------------------------
# ---------- Utilities ----------
# Text cleaning, hashing, and header/footer detection
# -------------------------------------------------------------

def clean_whitespace(text):
    """
    Normalize whitespace and remove excessive newlines.
    """
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()

def hash_id(path: Path):
    """
    Generate a short unique ID for a PDF based on name, size, and modification time.
    """
    stat = path.stat()
    return hashlib.sha1(f"{path.name}_{stat.st_mtime_ns}_{stat.st_size}".encode()).hexdigest()[:12]

def detect_headers_footers(pages_texts, sample_pages=6):
    """
    Heuristically detect repeated lines at top/bottom of pages (headers/footers).
    Returns a set of repeated lines to remove.
    """
    lines_freq = {}
    sample = pages_texts[:sample_pages]
    for p in sample:
        lines = [ln.strip() for ln in p["text"].splitlines() if ln.strip()]
        top = lines[:3]
        bottom = lines[-3:]
        for ln in top + bottom:
            lines_freq[ln] = lines_freq.get(ln, 0) + 1
    repeats = {ln for ln, c in lines_freq.items() if c >= 2 and len(ln) < 120}
    return repeats

def remove_headers_footers_from_page(text, repeats_set):
    """
    Remove detected header/footer lines from a page's text.
    """
    if not repeats_set:
        return text
    lines = text.splitlines()
    return "\n".join([ln for ln in lines if ln.strip() not in repeats_set])

# -------------------------------------------------------------
# ---------- Main PDF Processing ----------
# This function combines all steps:
# 1. Try text extraction
# 2. Detect pages needing OCR
# 3. Run OCR in parallel if needed
# 4. Clean text and remove headers/footers
# 5. Save as JSON
# -------------------------------------------------------------

def process_pdf(path: Path, out_dir: Path, force_ocr=False, min_text_len=300, dpi=150, tesseract_cmd=None):
    """
    Process a single PDF and save output as JSON.
    Skips already processed PDFs.
    """
    doc_id = hash_id(path)
    out_path = out_dir / f"{doc_id}.json"

    if out_path.exists():
        print(f"Skipping already processed PDF: {path.name}")
        return out_path

    print(f"\nProcessing {path.name}")
    pages = []
    engine = None

    # Try PDF text extractors
    if not force_ocr:
        try:
            pages = extract_with_pdfplumber(str(path))
            engine = "pdfplumber"
        except Exception:
            try:
                pages = extract_with_pymupdf(str(path))
                engine = "pymupdf"
            except Exception:
                pages = []

    # If both extractors failed, create empty placeholders
    if not pages:
        import fitz
        doc = fitz.open(str(path))
        pages = [{"page": i+1, "text": ""} for i in range(doc.page_count)]

    # Determine pages that need OCR
    combined = "\n".join([p["text"] for p in pages]).strip()
    needs_ocr = {p["page"] for p in pages if not p["text"].strip()}

    if force_ocr or len(combined) < min_text_len or needs_ocr:
        print(f"Running OCR on {len(needs_ocr)} pages...")
        images = pdf_to_images_fitz(str(path), dpi=dpi)
        ocr_pages = ocr_pages_parallel(
            images,
            pages_to_ocr=None if force_ocr else needs_ocr,
            tesseract_cmd=tesseract_cmd,
            debug_dir=out_dir / "debug" / doc_id
        )
        ocr_map = {p["page"]: p["text"] for p in ocr_pages}
        # merge OCR results with existing text
        pages = [{"page": p["page"], "text": ocr_map.get(p["page"], p["text"])} for p in pages]
        engine = "ocr"

    # Clean headers/footers
    repeats = detect_headers_footers(pages)
    cleaned_pages = []
    combined_text = []
    for p in pages:
        cleaned = clean_whitespace(remove_headers_footers_from_page(p["text"], repeats))
        cleaned_pages.append({"page": p["page"], "text": cleaned})
        combined_text.append(cleaned)

    # Create JSON output
    out_json = {
        "doc_id": doc_id,
        "source_file": path.name,
        "engine": engine,
        "pages": cleaned_pages,
        "text": "\n\n".join([t for t in combined_text if t]),
        "meta": {"path": str(path), "n_pages": len(cleaned_pages)}
    }

    # Save JSON
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_json, f, ensure_ascii=False, indent=2)

    print(f"Saved: {out_path} | engine: {engine} | chars: {len(out_json['text'])}")
    return out_path

# -------------------------------------------------------------
# ---------- Helper to find PDFs ----------
# -------------------------------------------------------------
def find_pdfs(pdf_dir: Path):
    """
    Returns all PDF files in a directory, sorted alphabetically.
    """
    return sorted([p for p in pdf_dir.iterdir() if p.suffix.lower() == ".pdf"])

# -------------------------------------------------------------
# ---------- CLI Entry Point ----------
# This is where the script execution begins.
# It parses command-line arguments, finds PDFs, and processes them.
# -------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Fast PDF -> JSON with OCR fallback (multi-processing)")
    parser.add_argument("--input", "-i", type=str, required=True, help="input directory with PDFs")
    parser.add_argument("--outdir", "-o", type=str, required=True, help="output directory")
    parser.add_argument("--force-ocr", action="store_true")
    parser.add_argument("--min-text", type=int, default=300, help="minimum text length to skip OCR")
    parser.add_argument("--dpi", type=int, default=150, help="DPI for OCR images")
    parser.add_argument("--tesseract-cmd", type=str, default=None, help="explicit path to tesseract exe")
    args = parser.parse_args()

    pdf_dir = Path(args.input)
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pdfs = find_pdfs(pdf_dir)
    if not pdfs:
        print("No PDFs found in", pdf_dir)
        return

    # Process PDFs one by one, showing a progress bar
    for pdf in tqdm(pdfs):
        try:
            process_pdf(pdf, out_dir, force_ocr=args.force_ocr, min_text_len=args.min_text,
                        dpi=args.dpi, tesseract_cmd=args.tesseract_cmd)
        except Exception as e:
            print(f"Error processing {pdf.name}: {e}")

if __name__ == "__main__":
    main()
