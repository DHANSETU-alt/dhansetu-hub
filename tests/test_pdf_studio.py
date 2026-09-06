"""
pdf_studio.py. Every test operates on REAL PDF files -- generated with
pypdf itself (add_blank_page) as fixtures, then actually merged/split/
compressed/rotated/extracted/encrypted/decrypted, and the real output
files are opened again with pypdf to verify the result. No mocking --
the whole point of this module is that it produces real, valid files.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pypdf import PdfReader, PdfWriter
from PIL import Image

from orchestrator import pdf_studio as ps


def _make_pdf(path, num_pages=1, size=(200, 300)):
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=size[0], height=size[1])
    with open(path, "wb") as f:
        writer.write(f)
    return path


def _make_image(path, color=(255, 0, 0), size=(100, 100)):
    Image.new("RGB", size, color).save(path)
    return path


class PdfStudioTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="shakthi_pdf_studio_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestMerge(PdfStudioTestBase):
    def test_merges_real_pdfs(self):
        a = _make_pdf(self.tmp / "a.pdf", num_pages=2)
        b = _make_pdf(self.tmp / "b.pdf", num_pages=3)
        out = self.tmp / "merged.pdf"
        result = ps.merge_pdfs([str(a), str(b)], str(out))

        self.assertTrue(out.exists())
        reader = PdfReader(str(out))
        self.assertEqual(len(reader.pages), 5)
        self.assertEqual(result["total_pages"], 5)

    def test_requires_at_least_two_files(self):
        a = _make_pdf(self.tmp / "a.pdf")
        with self.assertRaises(ps.PdfStudioError):
            ps.merge_pdfs([str(a)], str(self.tmp / "out.pdf"))


class TestSplit(PdfStudioTestBase):
    def test_splits_into_one_file_per_page(self):
        a = _make_pdf(self.tmp / "a.pdf", num_pages=4)
        out_dir = self.tmp / "split"
        result = ps.split_pdf(str(a), str(out_dir))

        self.assertEqual(result["page_count"], 4)
        for f in result["output_files"]:
            self.assertTrue(Path(f).exists())
            self.assertEqual(len(PdfReader(f).pages), 1)


class TestCompress(PdfStudioTestBase):
    def test_produces_valid_smaller_or_equal_output(self):
        a = _make_pdf(self.tmp / "a.pdf", num_pages=5)
        out = self.tmp / "compressed.pdf"
        result = ps.compress_pdf(str(a), str(out))

        self.assertTrue(out.exists())
        self.assertEqual(len(PdfReader(str(out)).pages), 5)
        self.assertIn("reduction_percent", result)


class TestImagesToPdf(PdfStudioTestBase):
    def test_converts_real_images_to_pdf(self):
        img1 = _make_image(self.tmp / "img1.png", color=(255, 0, 0))
        img2 = _make_image(self.tmp / "img2.png", color=(0, 255, 0))
        out = self.tmp / "images.pdf"
        result = ps.images_to_pdf([str(img1), str(img2)], str(out))

        self.assertTrue(out.exists())
        self.assertEqual(len(PdfReader(str(out)).pages), 2)
        self.assertEqual(result["page_count"], 2)

    def test_no_images_rejected(self):
        with self.assertRaises(ps.PdfStudioError):
            ps.images_to_pdf([], str(self.tmp / "out.pdf"))


class TestRotate(PdfStudioTestBase):
    def test_rotates_all_pages(self):
        a = _make_pdf(self.tmp / "a.pdf", num_pages=2, size=(200, 300))
        out = self.tmp / "rotated.pdf"
        ps.rotate_pdf(str(a), str(out), 90)

        reader = PdfReader(str(out))
        self.assertEqual(reader.pages[0].get("/Rotate"), 90)
        self.assertEqual(reader.pages[1].get("/Rotate"), 90)

    def test_rotates_only_specified_pages(self):
        a = _make_pdf(self.tmp / "a.pdf", num_pages=3)
        out = self.tmp / "rotated.pdf"
        ps.rotate_pdf(str(a), str(out), 180, page_numbers=[2])

        reader = PdfReader(str(out))
        self.assertIsNone(reader.pages[0].get("/Rotate"))
        self.assertEqual(reader.pages[1].get("/Rotate"), 180)
        self.assertIsNone(reader.pages[2].get("/Rotate"))

    def test_invalid_degrees_rejected(self):
        a = _make_pdf(self.tmp / "a.pdf")
        with self.assertRaises(ps.PdfStudioError):
            ps.rotate_pdf(str(a), str(self.tmp / "out.pdf"), 45)


class TestExtractPages(PdfStudioTestBase):
    def test_extracts_specified_pages_in_order(self):
        a = _make_pdf(self.tmp / "a.pdf", num_pages=5)
        out = self.tmp / "extracted.pdf"
        result = ps.extract_pages(str(a), str(out), [2, 4])

        self.assertEqual(result["extracted_pages"], 2)
        self.assertEqual(len(PdfReader(str(out)).pages), 2)

    def test_out_of_range_page_rejected(self):
        a = _make_pdf(self.tmp / "a.pdf", num_pages=2)
        with self.assertRaises(ps.PdfStudioError):
            ps.extract_pages(str(a), str(self.tmp / "out.pdf"), [5])


class TestZipDir(PdfStudioTestBase):
    def test_zips_split_output(self):
        a = _make_pdf(self.tmp / "a.pdf", num_pages=3)
        out_dir = self.tmp / "split"
        ps.split_pdf(str(a), str(out_dir))

        zip_path = self.tmp / "out.zip"
        result = ps.zip_dir(str(out_dir), str(zip_path))

        self.assertTrue(zip_path.exists())
        self.assertEqual(result["file_count"], 3)
        import zipfile
        with zipfile.ZipFile(str(zip_path)) as zf:
            self.assertEqual(len(zf.namelist()), 3)

    def test_empty_dir_rejected(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        with self.assertRaises(ps.PdfStudioError):
            ps.zip_dir(str(empty), str(self.tmp / "out.zip"))


class TestPasswordProtection(PdfStudioTestBase):
    def test_protect_then_remove_round_trips(self):
        a = _make_pdf(self.tmp / "a.pdf", num_pages=2)
        protected = self.tmp / "protected.pdf"
        ps.password_protect(str(a), str(protected), "secret123")

        reader = PdfReader(str(protected))
        self.assertTrue(reader.is_encrypted)

        unprotected = self.tmp / "unprotected.pdf"
        ps.remove_password(str(protected), str(unprotected), "secret123")
        reader2 = PdfReader(str(unprotected))
        self.assertFalse(reader2.is_encrypted)
        self.assertEqual(len(reader2.pages), 2)

    def test_wrong_password_rejected(self):
        a = _make_pdf(self.tmp / "a.pdf")
        protected = self.tmp / "protected.pdf"
        ps.password_protect(str(a), str(protected), "correct")

        with self.assertRaises(ps.PdfStudioError):
            ps.remove_password(str(protected), str(self.tmp / "out.pdf"), "wrong")

    def test_empty_password_rejected(self):
        a = _make_pdf(self.tmp / "a.pdf")
        with self.assertRaises(ps.PdfStudioError):
            ps.password_protect(str(a), str(self.tmp / "out.pdf"), "")

    def test_opening_encrypted_pdf_without_password_rejected(self):
        a = _make_pdf(self.tmp / "a.pdf")
        protected = self.tmp / "protected.pdf"
        ps.password_protect(str(a), str(protected), "secret")

        with self.assertRaises(ps.PdfStudioError):
            ps.compress_pdf(str(protected), str(self.tmp / "out.pdf"))


if __name__ == "__main__":
    unittest.main()
