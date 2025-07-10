# modules/clue_acquisition/acquirer.py
import os
import requests # For Search API
import json

# Attempt to import configurations and other modules
try:
    from config import main_config
    from config import clue_acquisition_config
    from modules.patent_parser import PatentFileParser
except ImportError as e:
    print(f"WARN: ClueAcquirer: Error importing dependent modules or configs: {e}. Using fallback defaults or functionality might be limited.")
    # Define fallback configurations if import fails
    class main_config: #type: ignore
        SIMULATE_LLM = True # Fallback, not directly used here but good for consistency
        # Any other critical configs that might be indirectly needed by PatentFileParser

    class clue_acquisition_config: #type: ignore
        ACQUISITION_MODE = "local"
        LOCAL_CLUE_DIRECTORY = "clue_files_fallback/"
        LOCAL_FILE_TYPES_TO_PARSE = ['.pdf', '.docx', '.doc', '.md', '.txt']
        LOCAL_PDF_OCR_ENABLED = False
        SEARCH_API_ENDPOINT = "http://fallback-search-api.com/search"
        SEARCH_API_KEY = "FALLBACK_API_KEY"
        SEARCH_API_QUERY_TEMPLATE = {"query_fields": ["title", "abstract"], "max_results": 10}
        SEARCH_API_RESPONSE_EXTRACTION_FIELDS = {"title": "title", "snippet": "snippet", "url": "link"}

    # Fallback PatentFileParser if the real one can't be imported
    class PatentFileParser: #type: ignore
        def __init__(self):
            print("WARN: ClueAcquirer: Using fallback PatentFileParser.")
        def parse_file(self, filepath, perform_ocr_if_applicable=None):
            return f"[FallbackParsed: {os.path.basename(filepath)} OCR: {perform_ocr_if_applicable}]"

class ClueAcquirer:
    def __init__(self):
        self.mode = clue_acquisition_config.ACQUISITION_MODE
        self.patent_parser = PatentFileParser() # Instantiate the actual parser

        # Local mode settings
        self.local_dir = getattr(clue_acquisition_config, 'LOCAL_CLUE_DIRECTORY', 'clues/') # Default if not set
        self.allowed_extensions = clue_acquisition_config.LOCAL_FILE_TYPES_TO_PARSE
        self.local_pdf_ocr = clue_acquisition_config.LOCAL_PDF_OCR_ENABLED

        # Search API settings
        self.api_endpoint = clue_acquisition_config.SEARCH_API_ENDPOINT
        self.api_key = clue_acquisition_config.SEARCH_API_KEY
        self.api_query_template = clue_acquisition_config.SEARCH_API_QUERY_TEMPLATE
        self.api_response_fields = clue_acquisition_config.SEARCH_API_RESPONSE_EXTRACTION_FIELDS

        print(f"INFO: ClueAcquirer initialized in '{self.mode}' mode.")

    def _acquire_from_local_files(self, source_paths):
        """
        Acquires and parses clues from a list of local file paths or a directory.
        Args:
            source_paths (list or str): A list of file paths, or a single directory path.
        Returns:
            list: A list of dictionaries, where each dict represents a clue:
                  {'source_type': 'local_file', 'source_path': filepath, 'parsed_text': '...', 'error': '...'}
        """
        clues = []
        files_to_process = []

        if isinstance(source_paths, str) and os.path.isdir(source_paths):
            print(f"INFO: ClueAcquirer: Scanning directory '{source_paths}' for local clues.")
            for root, _, files in os.walk(source_paths):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in self.allowed_extensions):
                        files_to_process.append(os.path.join(root, file))
        elif isinstance(source_paths, list):
            print(f"INFO: ClueAcquirer: Processing provided list of {len(source_paths)} local files.")
            files_to_process = source_paths
        else:
            msg = "Invalid source_paths for local acquisition. Must be a directory string or a list of file paths."
            print(f"ERROR: ClueAcquirer: {msg}")
            return [{'source_type': 'local_acquisition_error', 'error': msg}]

        if not files_to_process:
            print(f"WARN: ClueAcquirer: No files found to process in local mode for sources: {source_paths}")
            return []

        for filepath in files_to_process:
            if not any(filepath.lower().endswith(ext) for ext in self.allowed_extensions):
                print(f"INFO: ClueAcquirer: Skipping file '{filepath}' due to unsupported extension.")
                clues.append({
                    'source_type': 'local_file_skipped',
                    'source_path': filepath,
                    'parsed_text': None,
                    'error': 'Unsupported file extension'
                })
                continue

            print(f"INFO: ClueAcquirer: Parsing local file '{filepath}' (OCR for PDF: {self.local_pdf_ocr}).")
            parsed_text = self.patent_parser.parse_file(filepath, perform_ocr_if_applicable=self.local_pdf_ocr)

            clue_data = {
                'source_type': 'local_file',
                'source_identifier': filepath, # More generic identifier
                'parsed_text': None,
                'error': None
            }
            if isinstance(parsed_text, str) and parsed_text.startswith("[") and parsed_text.endswith("]"): # Error code from parser
                clue_data['error'] = parsed_text
                print(f"WARN: ClueAcquirer: Error parsing file {filepath}: {parsed_text}")
            else:
                clue_data['parsed_text'] = parsed_text

            clues.append(clue_data)

        return clues

    def _acquire_from_search_api(self, search_terms, target_company=None, excluded_companies=None, focus_areas=None):
        """
        Acquires clues from a configured Search API.
        (Framework implementation - actual API interaction and parsing needs to be robustly handled)
        Args:
            search_terms (str or list): Keywords to search for.
            target_company (str, optional): Specific company to target.
            excluded_companies (list, optional): Companies to exclude.
            focus_areas (list, optional): Specific technology domains or areas.
        Returns:
            list: A list of dictionaries, where each dict represents a clue from API.
                  {'source_type': 'search_api', 'source_identifier': 'url_or_api_id',
                   'title': '...', 'snippet': '...', 'raw_api_response': {...},
                   'parsed_text': '...', 'error': '...'}
        """
        clues = []
        print(f"INFO: ClueAcquirer: Acquiring clues from Search API. Search: '{search_terms}', Target: '{target_company}'")

        if not self.api_endpoint or self.api_endpoint == "YOUR_SEARCH_API_URL_HERE":
            msg = "Search API endpoint not configured."
            print(f"ERROR: ClueAcquirer: {msg}")
            return [{'source_type': 'search_api_error', 'error': msg}]

        # Construct query (this is highly dependent on the specific API)
        query_params = {}
        if isinstance(self.api_query_template, dict):
            query_params = self.api_query_template.copy() # Start with template defaults

        # Simple keyword integration, real API might need complex query language
        if isinstance(search_terms, list):
            query_params['q'] = " ".join(search_terms)
        else:
            query_params['q'] = search_terms

        if target_company:
            query_params['target_company'] = target_company # Example, API specific
        # Add more complex filtering for excluded_companies, focus_areas based on API capabilities

        headers = {
            "Accept": "application/json"
        }
        if self.api_key and self.api_key != "YOUR_SEARCH_API_KEY_HERE":
            headers["Authorization"] = f"Bearer {self.api_key}" # Example, could be X-API-Key, etc.

        try:
            response = requests.get(self.api_endpoint, params=query_params, headers=headers, timeout=20)
            response.raise_for_status() # Raise HTTPError for bad responses (4XX, 5XX)
            api_results = response.json() # Assuming API returns JSON

            # Process results (highly API specific)
            # Example: if api_results is a list of items or has an 'items' key
            items = api_results.get('items', []) if isinstance(api_results, dict) else api_results if isinstance(api_results, list) else []

            for item in items:
                clue_data = {
                    'source_type': 'search_api',
                    'source_identifier': item.get(self.api_response_fields.get('url', 'id'), 'N/A'), # URL or unique ID
                    'title': item.get(self.api_response_fields.get('title', 'title'), 'N/A'),
                    'snippet': item.get(self.api_response_fields.get('snippet', 'snippet'), 'N/A'),
                    'raw_api_response': item,
                    'parsed_text': None, # Requires further processing
                    'error': None
                }

                # Attempt to get full text if available directly or via a content field
                content_field_key = self.api_response_fields.get('content_field')
                full_text = item.get(content_field_key) if content_field_key else None

                if full_text:
                    clue_data['parsed_text'] = full_text # Assume it's plain text or pre-parsed
                elif clue_data['source_identifier'] and clue_data['source_identifier'].startswith('http'):
                    # If we have a URL and no direct full text, we might need to fetch and parse it
                    # This can be complex (HTML parsing, paywalls, dynamic content)
                    # For now, just mark it for potential later parsing or use snippet
                    print(f"INFO: ClueAcquirer: Search API result '{clue_data['title']}' has URL, may need further fetching/parsing.")
                    # As a placeholder, use snippet if no full text. In a real scenario, you might
                    # download the URL content and use self.patent_parser.parse_file(downloaded_html_path)
                    if not clue_data['parsed_text'] and clue_data['snippet']:
                         clue_data['parsed_text'] = f"Title: {clue_data['title']}\nSnippet: {clue_data['snippet']}"


                clues.append(clue_data)

            if not clues:
                print(f"INFO: ClueAcquirer: Search API returned no matching results for query: {query_params.get('q')}")


        except requests.exceptions.RequestException as e:
            error_msg = f"Search API request failed: {e}"
            print(f"ERROR: ClueAcquirer: {error_msg}")
            clues.append({'source_type': 'search_api_error', 'error': error_msg, 'details': str(e)})
        except json.JSONDecodeError as e:
            error_msg = f"Failed to decode Search API JSON response: {e}"
            print(f"ERROR: ClueAcquirer: {error_msg}")
            clues.append({'source_type': 'search_api_error', 'error': error_msg, 'raw_response_text': response.text if 'response' in locals() else 'N/A'})
        except Exception as e: # Catch-all for other unexpected errors during API processing
            error_msg = f"Unexpected error processing Search API results: {e}"
            print(f"ERROR: ClueAcquirer: {error_msg}")
            clues.append({'source_type': 'search_api_error', 'error': error_msg})

        return clues

    def acquire_clues(self, local_sources=None, search_params=None):
        """
        Main method to acquire clues based on the configured mode.
        Args:
            local_sources (list or str, optional): For 'local' mode. List of file paths or a directory.
                                                   If not provided, uses `clue_acquisition_config.LOCAL_CLUE_DIRECTORY`.
            search_params (dict, optional): For 'search_api' mode. Contains keys like:
                                            'search_terms', 'target_company',
                                            'excluded_companies', 'focus_areas'.
        Returns:
            list: A list of acquired clue dictionaries.
        """
        if self.mode == "local":
            if local_sources:
                return self._acquire_from_local_files(local_sources)
            elif os.path.exists(self.local_dir) and os.path.isdir(self.local_dir) : # Check if default dir exists
                print(f"INFO: ClueAcquirer: No local_sources provided, using default directory: {self.local_dir}")
                return self._acquire_from_local_files(self.local_dir)
            else:
                msg = f"Local mode selected, but no valid 'local_sources' provided and default directory '{self.local_dir}' not found or not a directory."
                print(f"ERROR: ClueAcquirer: {msg}")
                return [{'source_type': 'local_acquisition_error', 'error': msg}]
        elif self.mode == "search_api":
            if not search_params or not search_params.get('search_terms'):
                msg = "Search API mode selected, but 'search_params' (with 'search_terms') not provided."
                print(f"ERROR: ClueAcquirer: {msg}")
                return [{'source_type': 'search_api_error', 'error': msg}]
            return self._acquire_from_search_api(
                search_terms=search_params.get('search_terms'),
                target_company=search_params.get('target_company'),
                excluded_companies=search_params.get('excluded_companies'),
                focus_areas=search_params.get('focus_areas')
            )
        else:
            msg = f"Invalid acquisition mode: {self.mode}. Must be 'local' or 'search_api'."
            print(f"ERROR: ClueAcquirer: {msg}")
            return [{'source_type': 'configuration_error', 'error': msg}]

if __name__ == '__main__':
    print("--- ClueAcquirer Test ---")

    # --- Setup for local testing ---
    TEST_CLUES_DIR = "temp_clue_acquirer_test_files"
    os.makedirs(TEST_CLUES_DIR, exist_ok=True)
    with open(os.path.join(TEST_CLUES_DIR, "clue1.txt"), "w", encoding="utf-8") as f:
        f.write("This is text clue 1 about product Alpha.")
    with open(os.path.join(TEST_CLUES_DIR, "clue2.md"), "w", encoding="utf-8") as f:
        f.write("# Clue Two\nDetails about Beta project.")
    with open(os.path.join(TEST_CLUES_DIR, "clue3.pdf"), "w", encoding="utf-8") as f:
        f.write("Dummy PDF content for Gamma (real PDF needed for actual parsing).") # Not a real PDF
    with open(os.path.join(TEST_CLUES_DIR, "unsupported.dat"), "w") as f: f.write("dummy data")


    # --- Test Local Mode ---
    print("\n--- Testing Local Mode (directory scan) ---")
    # Temporarily override config for testing local dir if needed, or rely on its default
    # clue_acquisition_config.LOCAL_CLUE_DIRECTORY = TEST_CLUES_DIR
    # We will pass the path directly to acquire_clues for this test
    acquirer_local_test = ClueAcquirer() # Will init with default config mode

    # To specifically test local mode, we can either change config or call _acquire_from_local_files directly (for isolated test)
    # For a more integrated test of acquire_clues:
    acquirer_local_test.mode = "local" # Force mode for this test instance if default isn't local
    local_clues_dir_scan = acquirer_local_test.acquire_clues(local_sources=TEST_CLUES_DIR)
    print(f"Acquired {len(local_clues_dir_scan)} clues from directory scan:")
    for clue in local_clues_dir_scan:
        print(f"  Source: {clue.get('source_identifier')}, Error: {clue.get('error')}, Text snippet: { (clue.get('parsed_text') or '')[:50] }...")

    print("\n--- Testing Local Mode (file list) ---")
    file_list = [
        os.path.join(TEST_CLUES_DIR, "clue1.txt"),
        os.path.join(TEST_CLUES_DIR, "non_existent_clue.docx") # Test non-existent file
    ]
    local_clues_file_list = acquirer_local_test.acquire_clues(local_sources=file_list)
    print(f"Acquired {len(local_clues_file_list)} clues from file list:")
    for clue in local_clues_file_list:
        print(f"  Source: {clue.get('source_identifier')}, Error: {clue.get('error')}, Text snippet: { (clue.get('parsed_text') or '')[:50] }...")


    # --- Test Search API Mode (Simulated) ---
    print("\n--- Testing Search API Mode (Simulated - will likely fail or use fallback if endpoint is placeholder) ---")
    # To test this, you might need to mock 'requests.get' or have a test API endpoint
    # For now, we expect it to try and fail if endpoint is "YOUR_SEARCH_API_URL_HERE"

    # Create a new acquirer instance that might pick up a Search API mode from config if it was set there
    # Or force it:
    acquirer_api_test = ClueAcquirer()
    acquirer_api_test.mode = "search_api"
    # acquirer_api_test.api_endpoint = "http://your-test-api.com/search" # If you have a test endpoint
    # acquirer_api_test.api_key = "test_key"

    search_results = acquirer_api_test.acquire_clues(search_params={
        'search_terms': "new widget technology",
        'target_company': "Acme Corp"
    })
    print(f"Acquired {len(search_results)} clues from Search API:")
    for clue in search_results:
        print(f"  Source: {clue.get('source_identifier', clue.get('error'))}, Title: {clue.get('title')}, Snippet: {clue.get('snippet')}")


    # --- Clean up ---
    import shutil
    # shutil.rmtree(TEST_CLUES_DIR) # Comment out if you want to inspect files
    print("\n--- ClueAcquirer Test Complete (Remember to manually clean up test directory if not done automatically) ---")
