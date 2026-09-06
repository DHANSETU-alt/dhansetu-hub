"""
Dhansetu PDF Studio -- real PDF processing. pypdf (pure Python, no system
binary needed -- no qpdf/ghostscript on this machine and no Homebrew to
install one, checked live) handles merge/split/rotate/extract/encrypt/
decrypt natively; Pillow (already installed, used nowhere else in this
project) handles image-to-PDF.

Every function here takes real file paths and writes a real file --
nothing is mocked or simulated. Errors from a corrupt/password-mismatched
input are real pypdf exceptions, not swallowed.
"""
import zipfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from PIL import Image

from . import config

config.PDF_STUDIO_DIR.mkdir(exist_ok=True)


class PdfStudioError(RuntimeError):
    pass


def _open_reader(path: str, password: str = None) -> PdfReader:
    reader = PdfReader(path)
    if reader.is_encrypted:
        if not password:
            raise PdfStudioError(f"{path} is password-protected — a password is required")
        if reader.decrypt(password) == 0:
            raise PdfStudioError(f"incorrect password for {path}")
    return reader


def merge_pdfs(input_paths: list, output_path: str) -> dict:
    if len(input_paths) < 2:
        raise PdfStudioError("merge needs at least 2 input files")
    writer = PdfWriter()
    total_pages = 0
    for p in input_paths:
        reader = _open_reader(p)
        writer.append(reader)
        total_pages += len(reader.pages)
    with open(output_path, "wb") as f:
        writer.write(f)
    return {"output_path": output_path, "input_files": len(input_paths), "total_pages": total_pages}


def split_pdf(input_path: str, output_dir: str) -> dict:
    reader = _open_reader(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    stem = Path(input_path).stem
    for i, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        out_path = out_dir / f"{stem}_page{i}.pdf"
        with open(out_path, "wb") as f:
            writer.write(f)
        outputs.append(str(out_path))
    return {"output_files": outputs, "page_count": len(outputs)}


def compress_pdf(input_path: str, output_path: str) -> dict:
    reader = _open_reader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for page in writer.pages:
        page.compress_content_streams()  # lossless: re-encodes content streams more efficiently
    with open(output_path, "wb") as f:
        writer.write(f)
    before = Path(input_path).stat().st_size
    after = Path(output_path).stat().st_size
    return {"output_path": output_path, "size_before_bytes": before, "size_after_bytes": after,
            "reduction_percent": round(100 * (1 - after / before), 1) if before else 0}


def images_to_pdf(image_paths: list, output_path: str) -> dict:
    if not image_paths:
        raise PdfStudioError("no images given")
    images = []
    for p in image_paths:
        img = Image.open(p)
        if img.mode != "RGB":
            img = img.convert("RGB")
        images.append(img)
    images[0].save(output_path, save_all=True, append_images=images[1:])
    return {"output_path": output_path, "page_count": len(images)}


def rotate_pdf(input_path: str, output_path: str, degrees: int, page_numbers: list = None) -> dict:
    if degrees % 90 != 0:
        raise PdfStudioError(f"degrees must be a multiple of 90, got {degrees}")
    reader = _open_reader(input_path)
    writer = PdfWriter()
    target = set(page_numbers) if page_numbers else None
    for i, page in enumerate(reader.pages, start=1):
        if target is None or i in target:
            page.rotate(degrees)
        writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)
    return {"output_path": output_path, "rotated_pages": len(target) if target else len(reader.pages)}


def extract_pages(input_path: str, output_path: str, page_numbers: list) -> dict:
    if not page_numbers:
        raise PdfStudioError("no page numbers given")
    reader = _open_reader(input_path)
    total = len(reader.pages)
    invalid = [n for n in page_numbers if n < 1 or n > total]
    if invalid:
        raise PdfStudioError(f"page number(s) out of range (document has {total} pages): {invalid}")
    writer = PdfWriter()
    for n in page_numbers:
        writer.add_page(reader.pages[n - 1])
    with open(output_path, "wb") as f:
        writer.write(f)
    return {"output_path": output_path, "extracted_pages": len(page_numbers)}


def password_protect(input_path: str, output_path: str, password: str) -> dict:
    if not password:
        raise PdfStudioError("password is required")
    reader = _open_reader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    with open(output_path, "wb") as f:
        writer.write(f)
    return {"output_path": output_path}


def zip_dir(input_dir: str, output_zip_path: str) -> dict:
    """Bundles split_pdf's one-file-per-page output into a single download
    -- the browser download flow needs one file, not N."""
    in_dir = Path(input_dir)
    files = sorted(in_dir.glob("*.pdf"))
    if not files:
        raise PdfStudioError(f"no PDF files found in {input_dir}")
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.name)
    return {"output_path": output_zip_path, "file_count": len(files)}


def remove_password(input_path: str, output_path: str, password: str) -> dict:
    reader = _open_reader(input_path, password=password)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)
    return {"output_path": output_path}
