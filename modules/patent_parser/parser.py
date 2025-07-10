# modules/patent_parser/parser.py
import os
import PyPDF2
import pdfplumber
import docx # python-docx
import markdown
from bs4 import BeautifulSoup # For HTML parsing
from PIL import Image # For OCR with pytesseract
import pytesseract # For OCR

# Attempt to import configurations
try:
    from config import main_config
    from config import patent_parser_config
except ImportError:
    print("WARN: PatentFileParser: Could not import main_config or patent_parser_config. Using fallback defaults.")
    # Define fallback configurations if import fails (e.g., during isolated testing or if setup is incomplete)
    class main_config: #type: ignore
        TESSERACT_CMD = None # Or 'tesseract' if it's expected in PATH
        SIMULATE_LLM = True # Fallback, though not directly used by parser

    class patent_parser_config: #type: ignore
        DEFAULT_OCR_ENABLED = False
        OCR_LANGUAGES = "eng"
        PDF_PARSING_STRATEGY = "pdfplumber" # "pypdf2" or "pdfplumber"


class PatentFileParser:
    def __init__(self):
        # Configure Tesseract if path is provided in main_config
        if hasattr(main_config, 'TESSERACT_CMD') and main_config.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = main_config.TESSERACT_CMD
            # Test if Tesseract is working by trying to get its version
            try:
                pytesseract.get_tesseract_version()
                print(f"PatentFileParser: Tesseract configured from: {main_config.TESSERACT_CMD} and version detected.")
            except pytesseract.TesseractNotFoundError:
                print(f"WARN: PatentFileParser: Tesseract not found at '{main_config.TESSERACT_CMD}' or not in PATH. OCR will fail.")
            except Exception as e: # Catch other potential errors like permission issues
                print(f"WARN: PatentFileParser: Tesseract command ('{main_config.TESSERACT_CMD}') problem: {e}. OCR may fail.")

        self.default_ocr_enabled = patent_parser_config.DEFAULT_OCR_ENABLED
        self.ocr_languages = patent_parser_config.OCR_LANGUAGES
        # self.pdf_parsing_strategy = patent_parser_config.PDF_PARSING_STRATEGY

    def _extract_text_from_pdf_simple(self, pdf_path):
        text = ""
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted:
                    try:
                        reader.decrypt('')
                    except Exception as e:
                        print(f"WARN: PatentFileParser: Could not decrypt PDF {pdf_path} with empty password: {e}")
                        # return "[PDF_ENCRYPTED_NO_PW]" # Or handle as error
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() or ""
            if not text.strip() and len(reader.pages) > 0:
                print(f"INFO: PatentFileParser: PyPDF2 extracted no text from {pdf_path}. Consider OCR if it's image-based.")
        except Exception as e:
            print(f"ERROR: PatentFileParser: Error reading PDF with PyPDF2 {pdf_path}: {e}")
            # return "[PyPDF2_READ_ERROR]"
        return text

    def _extract_text_from_pdf_plumber(self, pdf_path, perform_ocr=False):
        text = ""
        ocr_performed_on_page = False
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
                    if page_text:
                        text += page_text + "\n"

                    # OCR Integration
                    if perform_ocr and (not page_text or len(page_text.strip()) < 20): # Perform OCR if little/no text or forced
                        if not pytesseract.pytesseract.tesseract_cmd:
                            print(f"WARN: PatentFileParser: Tesseract not configured, skipping OCR for page {i+1} of {pdf_path}.")
                            continue
                        try:
                            # Convert page to image for OCR
                            page_image = page.to_image(resolution=300) # Requires Pillow
                            ocr_text = page_image.debug_tablefinder() #This is for table not text
                            ocr_text = pytesseract.image_to_string(page_image.original, lang=self.ocr_languages)
                            if ocr_text:
                                print(f"INFO: PatentFileParser: OCR performed on page {i+1} of {pdf_path} (lang: {self.ocr_languages}).")
                                text += "\n--- OCR Text Page " + str(i+1) + " ---\n" + ocr_text + "\n"
                                ocr_performed_on_page = True
                            else:
                                print(f"INFO: PatentFileParser: OCR on page {i+1} of {pdf_path} yielded no text.")
                        except pytesseract.TesseractNotFoundError:
                            print(f"WARN: PatentFileParser: Tesseract not found or not configured. Cannot perform OCR on {pdf_path}.")
                            perform_ocr = False # Stop trying OCR if tesseract is not found
                        except Exception as e:
                            print(f"ERROR: PatentFileParser: OCR failed for page {i+1} of {pdf_path}: {e}")
            if not text.strip() and not ocr_performed_on_page and len(pdf.pages) > 0:
                 print(f"INFO: PatentFileParser: Pdfplumber extracted no text from {pdf_path} and OCR was not effective or not run.")

        except Exception as e:
            print(f"ERROR: PatentFileParser: Error reading PDF with pdfplumber {pdf_path}: {e}")
            # return "[PDFPLUMBER_READ_ERROR]"
        return text

    def _extract_text_from_docx(self, docx_path):
        text = ""
        try:
            document = docx.Document(docx_path)
            for para in document.paragraphs:
                text += para.text + "\n"
        except docx.opc.exceptions.PackageNotFoundError:
            print(f"ERROR: PatentFileParser: DOCX file not found or is not a valid package: {docx_path}")
            return "[DOCX_PACKAGE_NOT_FOUND_ERROR]"
        except Exception as e:
            print(f"ERROR: PatentFileParser: Error reading DOCX {docx_path}: {e}")
            return "[DOCX_READ_ERROR]"
        return text

    def _extract_text_from_markdown(self, md_path):
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            # Option to convert to plain text, for now return raw markdown
            # html = markdown.markdown(md_content)
            # soup = BeautifulSoup(html, 'html.parser')
            # return soup.get_text()
            return md_content
        except Exception as e:
            print(f"ERROR: PatentFileParser: Error reading Markdown {md_path}: {e}")
            return "[MARKDOWN_READ_ERROR]"

    def _extract_text_from_txt(self, txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f: # Added errors='ignore' for robustness
                return f.read()
        except Exception as e:
            print(f"ERROR: PatentFileParser: Error reading TXT {txt_path}: {e}")
            return "[TXT_READ_ERROR]"

    def _extract_text_from_html(self, html_path):
        try:
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()

            # Get text, joining lines and stripping extra whitespace
            text = soup.get_text(separator='\n', strip=True)
            return text
        except Exception as e:
            print(f"ERROR: PatentFileParser: Error reading/parsing HTML {html_path}: {e}")
            return "[HTML_READ_ERROR]"

    def parse_file(self, filepath, perform_ocr_if_applicable=None):
        """
        Parses the given file and extracts text content.
        Args:
            filepath (str): Path to the file.
            perform_ocr_if_applicable (bool, optional): Override default OCR setting for this parse.
                                                        If None, uses self.default_ocr_enabled.
        Returns:
            str: Extracted text content, or an error message string.
                 Returns None if the file extension is not supported.
        """
        if not os.path.exists(filepath):
            print(f"ERROR: PatentFileParser: File not found at {filepath}")
            return "[FILE_NOT_FOUND]"
        if not os.path.isfile(filepath):
            print(f"ERROR: PatentFileParser: Path is not a file {filepath}")
            return "[PATH_IS_NOT_A_FILE]"


        ext = os.path.splitext(filepath)[1].lower()
        extracted_text = None

        ocr_flag = self.default_ocr_enabled
        if perform_ocr_if_applicable is not None:
            ocr_flag = perform_ocr_if_applicable

        print(f"INFO: PatentFileParser: Parsing file '{os.path.basename(filepath)}' with extension '{ext}'. OCR for PDF: {ocr_flag}")

        if ext == '.pdf':
            # if self.pdf_parsing_strategy == "pypdf2":
            #    extracted_text = self._extract_text_from_pdf_simple(filepath)
            # else: # Default to pdfplumber
            extracted_text = self._extract_text_from_pdf_plumber(filepath, perform_ocr=ocr_flag)
        elif ext == '.docx':
            extracted_text = self._extract_text_from_docx(filepath)
        elif ext == '.doc':
            # .doc is harder to parse directly in Python without external tools like antiword or libreoffice
            # For now, we can return a message or try a very basic extraction if possible.
            print(f"WARN: PatentFileParser: '.doc' files have limited support. Attempting basic text extraction. For best results, convert to .docx or .pdf: {filepath}")
            # Placeholder: could try to read as txt with error handling
            # As a very basic fallback, could try treating it as a text file, though it will be mostly binary garbage.
            # extracted_text = self._extract_text_from_txt(filepath) # This is usually not useful for .doc
            extracted_text = "[DOC_FORMAT_UNSUPPORTED_CONVERT_TO_DOCX]"
        elif ext == '.md':
            extracted_text = self._extract_text_from_markdown(filepath)
        elif ext == '.txt':
            extracted_text = self._extract_text_from_txt(filepath)
        elif ext in ['.html', '.htm']:
            extracted_text = self._extract_text_from_html(filepath)
        else:
            print(f"WARN: PatentFileParser: No specific parser for extension {ext} of file {filepath}. Returning None.")
            return f"[UNSUPPORTED_FILE_EXTENSION: {ext}]"

        if extracted_text is None: # Should ideally be caught by specific error returns
            print(f"ERROR: PatentFileParser: Parser for {ext} returned None unexpectedly for file {filepath}")
            return "[PARSING_RETURNED_NONE]"

        return extracted_text

if __name__ == '__main__':
    # Example usage for local testing (requires creating these files or changing paths)
    print("--- PatentFileParser Test ---")
    parser = PatentFileParser()

    # Create dummy files for testing
    TEST_DIR = "parser_test_files"
    os.makedirs(TEST_DIR, exist_ok=True)

    with open(os.path.join(TEST_DIR, "test.txt"), "w", encoding="utf-8") as f:
        f.write("This is a simple text file.\nHello World.")

    with open(os.path.join(TEST_DIR, "test.md"), "w", encoding="utf-8") as f:
        f.write("# Markdown File\n\nThis is a test markdown file with some *emphasis* and **bold** text.")

    # Note: Creating valid .pdf, .docx, .html programmatically for robust testing is complex.
    # It's better to have actual sample files.
    # For now, we'll mainly test .txt and .md and the error handling for missing files.

    print("\nTesting TXT file:")
    txt_content = parser.parse_file(os.path.join(TEST_DIR, "test.txt"))
    print(f"Content:\n{txt_content}")

    print("\nTesting Markdown file:")
    md_content = parser.parse_file(os.path.join(TEST_DIR, "test.md"))
    print(f"Content:\n{md_content}")

    print("\nTesting Non-existent file:")
    non_existent_content = parser.parse_file(os.path.join(TEST_DIR, "non_existent.pdf"))
    print(f"Content: {non_existent_content}")

    print("\nTesting Unsupported extension:")
    unsupported_content = parser.parse_file(os.path.join(TEST_DIR, "test.xyz")) # Create a dummy file for this if needed
    with open(os.path.join(TEST_DIR, "test.xyz"), "w") as f: f.write("dummy")
    unsupported_content = parser.parse_file(os.path.join(TEST_DIR, "test.xyz"))
    print(f"Content: {unsupported_content}")

    # To test PDF/DOCX/HTML/OCR, you would need to:
    # 1. Ensure python-docx, pdfplumber, pytesseract, Pillow, BeautifulSoup4 are installed.
    # 2. Ensure Tesseract OCR engine is installed and configured (TESSERACT_CMD in main_config.py).
    # 3. Place sample files (e.g., sample.pdf, sample_ocr.pdf, sample.docx, sample.html) in TEST_DIR.
    # Example (manual setup needed):
    # sample_pdf_path = os.path.join(TEST_DIR, "sample.pdf")
    # if os.path.exists(sample_pdf_path):
    #     print(f"\nTesting PDF file: {sample_pdf_path}")
    #     pdf_content = parser.parse_file(sample_pdf_path, perform_ocr_if_applicable=False) # Test without OCR
    #     print(f"Content (no OCR):\n{pdf_content[:300]}...")
    #     pdf_content_ocr = parser.parse_file(sample_pdf_path, perform_ocr_if_applicable=True) # Test with OCR
    #     print(f"Content (with OCR if applicable):\n{pdf_content_ocr[:300]}...")
    # else:
    #     print(f"\nSkipping PDF test: {sample_pdf_path} not found.")

    # Clean up dummy files
    # import shutil
    # shutil.rmtree(TEST_DIR)
    print("\n--- Test Complete ---")
