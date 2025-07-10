import unittest
import os
import shutil
from modules.patent_parser import PatentFileParser
# Import configs to potentially modify them for testing or assert their defaults
from config import main_config, patent_parser_config

class TestPatentFileParser(unittest.TestCase):
    TEST_DIR = "temp_parser_test_files"

    @classmethod
    def setUpClass(cls):
        os.makedirs(cls.TEST_DIR, exist_ok=True)
        # Create some dummy files for parsing
        with open(os.path.join(cls.TEST_DIR, "test.txt"), "w", encoding="utf-8") as f:
            f.write("This is a simple text file.")
        with open(os.path.join(cls.TEST_DIR, "test.md"), "w", encoding="utf-8") as f:
            f.write("# Markdown Test")
        with open(os.path.join(cls.TEST_DIR, "test.html"), "w", encoding="utf-8") as f:
            f.write("<html><head><title>Test</title></head><body><p>Hello HTML</p><script>alert('hi')</script></body></html>")
        # Dummy docx and pdf for testing extension handling (actual parsing needs real files and libs)
        with open(os.path.join(cls.TEST_DIR, "test.docx"), "w") as f: f.write("dummy docx")
        with open(os.path.join(cls.TEST_DIR, "test.pdf"), "w") as f: f.write("dummy pdf") # Not a real PDF
        with open(os.path.join(cls.TEST_DIR, "test.doc"), "w") as f: f.write("dummy doc")


    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.TEST_DIR):
            shutil.rmtree(cls.TEST_DIR)

    def setUp(self):
        self.parser = PatentFileParser()
        # You can override config values for specific tests if needed, e.g.,
        # self.original_ocr_enabled = patent_parser_config.DEFAULT_OCR_ENABLED
        # patent_parser_config.DEFAULT_OCR_ENABLED = True

    def tearDown(self):
        # Restore any config values if changed in setUp/test
        # patent_parser_config.DEFAULT_OCR_ENABLED = self.original_ocr_enabled
        pass

    def test_parse_txt_file(self):
        filepath = os.path.join(self.TEST_DIR, "test.txt")
        content = self.parser.parse_file(filepath)
        self.assertEqual(content, "This is a simple text file.")

    def test_parse_md_file(self):
        filepath = os.path.join(self.TEST_DIR, "test.md")
        content = self.parser.parse_file(filepath)
        self.assertEqual(content, "# Markdown Test")

    def test_parse_html_file(self):
        filepath = os.path.join(self.TEST_DIR, "test.html")
        content = self.parser.parse_file(filepath)
        self.assertIn("Hello HTML", content)
        self.assertNotIn("<script>", content) # Check if script tags are removed

    def test_parse_unsupported_file(self):
        filepath = os.path.join(self.TEST_DIR, "unsupported.xyz")
        with open(filepath, "w") as f: f.write("dummy")
        content = self.parser.parse_file(filepath)
        self.assertEqual(content, "[UNSUPPORTED_FILE_EXTENSION: .xyz]")
        os.remove(filepath)

    def test_file_not_found(self):
        content = self.parser.parse_file("non_existent_file.txt")
        self.assertEqual(content, "[FILE_NOT_FOUND]")

    def test_parse_doc_file_placeholder(self):
        # Tests the placeholder behavior for .doc files
        filepath = os.path.join(self.TEST_DIR, "test.doc")
        content = self.parser.parse_file(filepath)
        self.assertEqual(content, "[DOC_FORMAT_UNSUPPORTED_CONVERT_TO_DOCX]")

    # More tests could be added for actual DOCX and PDF parsing,
    # but they would require valid sample files and all dependencies installed.
    # For OCR, one would need Tesseract installed and configured.

    def test_pdf_parsing_ocr_handling(self):
        # This test mainly checks the path for OCR, not the OCR quality itself without Tesseract
        filepath = os.path.join(self.TEST_DIR, "test.pdf") # This is a dummy PDF

        # Scenario 1: OCR disabled by default (or by explicit False)
        original_ocr_setting = patent_parser_config.DEFAULT_OCR_ENABLED
        patent_parser_config.DEFAULT_OCR_ENABLED = False
        self.parser = PatentFileParser() # Re-init to pick up config change

        # With dummy PDF, plumber might return empty or error. We test the flow.
        # We expect it not to try OCR if not enabled.
        # Actual text extraction from a dummy pdf is unreliable, focus on OCR path.
        # We'd need to mock pytesseract to truly test calls.
        content_no_ocr = self.parser.parse_file(filepath, perform_ocr_if_applicable=False)
        # print(f"Content no OCR: {content_no_ocr}") # For debugging
        self.assertTrue(isinstance(content_no_ocr, str)) # Should return string (empty or error code)

        # Scenario 2: OCR enabled by argument
        # This will print warnings if Tesseract is not found, which is expected in CI without Tesseract
        content_with_ocr_arg = self.parser.parse_file(filepath, perform_ocr_if_applicable=True)
        # print(f"Content with OCR arg: {content_with_ocr_arg}") # For debugging
        self.assertTrue(isinstance(content_with_ocr_arg, str))

        patent_parser_config.DEFAULT_OCR_ENABLED = original_ocr_setting # Restore


if __name__ == '__main__':
    unittest.main()
