# core/file_parser.py
import os
import PyPDF2
import pdfplumber
# import docx # python-docx
# from PIL import Image
# import pytesseract
import markdown

from config import settings # To get TESSERACT_CMD if needed

# Configure pytesseract if it's going to be used
# if hasattr(settings, 'TESSERACT_CMD'):
#     pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

def extract_text_from_pdf_simple(pdf_path):
    """
    Extracts text from a PDF file using PyPDF2.
    This method is fast but may not capture complex layouts or scanned images well.
    """
    text = ""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text() or ""
    except Exception as e:
        print(f"Error reading PDF with PyPDF2 {pdf_path}: {e}")
        # Fallback or re-raise might be needed
    return text

def extract_text_from_pdf_plumber(pdf_path,perform_ocr=False):
    """
    Extracts text from a PDF file using pdfplumber.
    pdfplumber is generally better for layout preservation and can integrate with OCR.
    """
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text(x_tolerance=2, y_tolerance=2) # Basic text extraction
                if page_text:
                    text += page_text + "\n"

                # TODO: OCR Integration - Placeholder
                # if perform_ocr or not page_text.strip(): # If no text or OCR is forced
                #     print(f"Page {i+1} of {pdf_path} might need OCR or is empty.")
                #     # images = page.images
                #     # For OCR on full page if needed:
                #     # im = page.to_image(resolution=300) # Requires Pillow
                #     # ocr_text = pytesseract.image_to_string(im.original, lang='chi_sim+eng') # Example langs
                #     # text += ocr_text + "\n"
                #     pass
    except Exception as e:
        print(f"Error reading PDF with pdfplumber {pdf_path}: {e}")
    return text


def extract_text_from_docx(docx_path):
    """
    Extracts text from a DOCX file.
    (Requires python-docx library)
    """
    text = ""
    try:
        # from docx import Document # Local import to avoid error if not installed during placeholder phase
        # doc = Document(docx_path)
        # for para in doc.paragraphs:
        #     text += para.text + "\n"
        # Placeholder implementation:
        return f"Simulated DOCX text from {os.path.basename(docx_path)}"
    except ImportError:
        print("python-docx library is not installed. DOCX parsing will be skipped.")
        return "[python-docx not installed]"
    except Exception as e:
        print(f"Error reading DOCX {docx_path}: {e}")
    return text

def extract_text_from_markdown(md_path):
    """
    Extracts text from a Markdown file. (Essentially reads it, could strip markdown for plain text)
    """
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        # For now, return raw markdown. If plain text is needed:
        # html = markdown.markdown(md_content)
        # from bs4 import BeautifulSoup
        # soup = BeautifulSoup(html, 'html.parser')
        # return soup.get_text()
        return md_content # Return raw markdown for now
    except Exception as e:
        print(f"Error reading Markdown {md_path}: {e}")
    return ""

def extract_text_from_txt(txt_path):
    """
    Extracts text from a plain text file.
    """
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading TXT {txt_path}: {e}")
    return ""

def extract_text_from_html(html_path):
    """
    Extracts text from an HTML file.
    """
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        # from bs4 import BeautifulSoup # To get clean text
        # soup = BeautifulSoup(html_content, 'html.parser')
        # return soup.get_text(separator='\n', strip=True)
        # For now, return raw HTML or a placeholder
        return f"Simulated HTML text from {os.path.basename(html_path)} (raw content below):\n{html_content[:1000]}..."
    except ImportError:
        print("BeautifulSoup4 library is not installed. HTML parsing will be basic.")
        with open(html_path, 'r', encoding='utf-8') as f: # Fallback to raw read
            return f.read()
    except Exception as e:
        print(f"Error reading HTML {html_path}: {e}")
    return ""


def get_parser_for_file(filepath):
    """Returns the appropriate parsing function based on file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.pdf':
        # return extract_text_from_pdf_simple # Or choose plumber by default
        return extract_text_from_pdf_plumber
    elif ext in ['.doc', '.docx']:
        return extract_text_from_docx
    elif ext == '.md':
        return extract_text_from_markdown
    elif ext == '.txt':
        return extract_text_from_txt
    elif ext in ['.html', '.htm']:
        return extract_text_from_html
    else:
        print(f"No specific parser for extension {ext} of file {filepath}. Treating as plain text if possible.")
        # Fallback to try reading as text, or return None
        return extract_text_from_txt # Or a more generic binary-to-text attempt

def extract_patent_text(patent_filepath):
    """
    Extracts text from the main patent document.
    This might have more specific logic in the future (e.g., identifying claims sections).
    """
    parser = get_parser_for_file(patent_filepath)
    if parser:
        print(f"Parsing patent file: {patent_filepath} using {parser.__name__}")
        return parser(patent_filepath)
    return None

def extract_evidence_texts(evidence_filepaths):
    """
    Extracts text from a list of evidence documents.
    Returns a dictionary obstáculos {filepath: text_content}.
    """
    extracted_texts = {}
    for filepath in evidence_filepaths:
        parser = get_parser_for_file(filepath)
        if parser:
            print(f"Parsing evidence file: {filepath} using {parser.__name__}")
            extracted_texts[filepath] = parser(filepath)
        else:
            extracted_texts[filepath] = None
            print(f"Could not find a suitable parser for evidence file: {filepath}")
    return extracted_texts

if __name__ == '__main__':
    # Placeholder for local testing of parsers
    # Create dummy files or point to existing test files
    print("File parser module. Run `app.py` to use the system.")
    # Example (requires creating these files or changing paths):
    # test_pdf = "../uploads/example.pdf" # Change to an actual PDF
    # if os.path.exists(test_pdf):
    #     print(f"\nTesting PDF (Plumber): {test_pdf}")
    #     text = extract_text_from_pdf_plumber(test_pdf)
    #     print(text[:500] + "..." if text else "No text extracted")

    # test_docx = "../uploads/example.docx" # Change to an actual DOCX
    # if os.path.exists(test_docx):
    #     print(f"\nTesting DOCX: {test_docx}")
    #     text = extract_text_from_docx(test_docx)
    #     print(text[:500] + "..." if text else "No text extracted")

    # test_md = "../README.md"
    # if os.path.exists(test_md):
    #     print(f"\nTesting Markdown: {test_md}")
    #     text = extract_text_from_markdown(test_md)
    #     print(text[:500] + "..." if text else "No text extracted")
    pass
