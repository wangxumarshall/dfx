# Configuration for the Infringement Clue Acquisition and Parsing Module

# Mode: "local" or "search_api"
ACQUISITION_MODE = "local" # Default to local acquisition

# --- Settings for "local" mode ---
# Default directory to scan for local clue files (can be overridden by user input)
# LOCAL_CLUE_DIRECTORY = "clue_files/" # Example path
# File types to parse in local mode
LOCAL_FILE_TYPES_TO_PARSE = ['.pdf', '.docx', '.doc', '.md', '.txt']
# Whether to use OCR for PDFs in local mode (references patent_parser_config for actual OCR settings)
LOCAL_PDF_OCR_ENABLED = False


# --- Settings for "search_api" mode ---
SEARCH_API_ENDPOINT = "YOUR_SEARCH_API_URL_HERE"
SEARCH_API_KEY = "YOUR_SEARCH_API_KEY_HERE" # Store sensitive keys securely (e.g., env variables)
# Template for search queries, if needed. Example: {"query": "{keywords}", "company": "{target_company}"}
SEARCH_API_QUERY_TEMPLATE = {
    "query_fields": ["title", "abstract", "full_text"], # Fields to search in
    "max_results": 20
}
# Fields to extract from API response
SEARCH_API_RESPONSE_EXTRACTION_FIELDS = {
    "title": "title",
    "snippet": "snippet",
    "url": "url",
    "content_field": "full_text_content" # Field from which to get main text for parsing
}
