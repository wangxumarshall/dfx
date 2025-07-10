import unittest
import os
import shutil
from unittest.mock import patch, MagicMock
import requests # Added import

from modules.clue_acquisition import ClueAcquirer
# Import configs to potentially modify them for testing
from config import clue_acquisition_config, main_config

class TestClueAcquirer(unittest.TestCase):
    TEST_DIR = "temp_clue_acquirer_tests"
    LOCAL_CLUES_SUBDIR = "local_clues"

    @classmethod
    def setUpClass(cls):
        os.makedirs(os.path.join(cls.TEST_DIR, cls.LOCAL_CLUES_SUBDIR), exist_ok=True)
        with open(os.path.join(cls.TEST_DIR, cls.LOCAL_CLUES_SUBDIR, "clue1.txt"), "w", encoding="utf-8") as f:
            f.write("Text content of clue 1.")
        with open(os.path.join(cls.TEST_DIR, cls.LOCAL_CLUES_SUBDIR, "clue2.md"), "w", encoding="utf-8") as f:
            f.write("## Markdown Clue 2")
        with open(os.path.join(cls.TEST_DIR, cls.LOCAL_CLUES_SUBDIR, "unsupported.dat"), "w") as f:
            f.write("dummy")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.TEST_DIR):
            shutil.rmtree(cls.TEST_DIR)

    def setUp(self):
        # Store original config values to restore them later
        self.original_mode = clue_acquisition_config.ACQUISITION_MODE
        self.original_local_dir = getattr(clue_acquisition_config, 'LOCAL_CLUE_DIRECTORY', None)
        self.original_simulate_llm = main_config.SIMULATE_LLM

        # Default to simulating LLM for PatentFileParser used internally by ClueAcquirer
        main_config.SIMULATE_LLM = True
        self.acquirer = ClueAcquirer()

    def tearDown(self):
        # Restore original config values
        clue_acquisition_config.ACQUISITION_MODE = self.original_mode
        if self.original_local_dir is not None:
            clue_acquisition_config.LOCAL_CLUE_DIRECTORY = self.original_local_dir
        else:
            if hasattr(clue_acquisition_config, 'LOCAL_CLUE_DIRECTORY'):
                delattr(clue_acquisition_config, 'LOCAL_CLUE_DIRECTORY')
        main_config.SIMULATE_LLM = self.original_simulate_llm


    def test_acquire_from_local_directory(self):
        clue_acquisition_config.ACQUISITION_MODE = "local"
        # The ClueAcquirer itself instantiates PatentFileParser, which will use main_config.SIMULATE_LLM
        # PatentFileParser's __init__ prints tesseract status, which is fine.

        # Test with the directory created in setUpClass
        clues_dir = os.path.join(self.TEST_DIR, self.LOCAL_CLUES_SUBDIR)
        self.acquirer = ClueAcquirer() # Re-init to pick up mode change

        results = self.acquirer.acquire_clues(local_sources=clues_dir)

        self.assertEqual(len(results), 2) # txt, md. unsupported.dat is skipped by ClueAcquirer's extension check

        txt_found = False
        md_found = False

        for r in results:
            if "clue1.txt" in r.get("source_identifier", ""):
                txt_found = True
                self.assertIsNone(r.get("error"))
                # PatentFileParser used by ClueAcquirer returns actual content for .txt
                self.assertIn("Text content of clue 1.", r.get("parsed_text", ""))
            elif "clue2.md" in r.get("source_identifier", ""):
                md_found = True
                self.assertIsNone(r.get("error"))
                self.assertIn("## Markdown Clue 2", r.get("parsed_text", ""))

        self.assertTrue(txt_found, "TXT clue not found or processed incorrectly")
        self.assertTrue(md_found, "MD clue not found or processed incorrectly")


    def test_acquire_from_local_file_list(self):
        clue_acquisition_config.ACQUISITION_MODE = "local"
        self.acquirer = ClueAcquirer() # Re-init

        file_list = [
            os.path.join(self.TEST_DIR, self.LOCAL_CLUES_SUBDIR, "clue1.txt"),
            "non_existent_file.pdf"
        ]
        results = self.acquirer.acquire_clues(local_sources=file_list)
        self.assertEqual(len(results), 2)

        self.assertIn("clue1.txt", results[0].get("source_identifier", ""))
        self.assertIsNotNone(results[0].get("parsed_text"))
        self.assertIsNone(results[0].get("error"))

        self.assertIn("non_existent_file.pdf", results[1].get("source_identifier", ""))
        self.assertIsNone(results[1].get("parsed_text")) # Should be None as file not found
        self.assertEqual(results[1].get("error"), "[FILE_NOT_FOUND]")


    @patch('modules.clue_acquisition.acquirer.requests.get')
    def test_acquire_from_search_api_success(self, mock_requests_get):
        clue_acquisition_config.ACQUISITION_MODE = "search_api"
        clue_acquisition_config.SEARCH_API_ENDPOINT = "http://fakeapi.com/search"
        clue_acquisition_config.SEARCH_API_KEY = "fakekey"
        clue_acquisition_config.SEARCH_API_RESPONSE_EXTRACTION_FIELDS = {
            "title": "title", "snippet": "snippet", "url": "link", "content_field": "full_text"
        }
        self.acquirer = ClueAcquirer() # Re-init

        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"title": "Result 1", "snippet": "Snippet for 1", "link": "http://example.com/1", "full_text": "Full text for 1"},
                {"title": "Result 2", "snippet": "Snippet for 2", "link": "http://example.com/2"} # No full_text
            ]
        }
        mock_requests_get.return_value = mock_response

        search_params = {'search_terms': "test query"}
        results = self.acquirer.acquire_clues(search_params=search_params)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], "Result 1")
        self.assertEqual(results[0]['parsed_text'], "Full text for 1")
        self.assertEqual(results[1]['title'], "Result 2")
        # For result 2, parsed_text should be a combination of title and snippet as fallback
        self.assertIn("Title: Result 2", results[1]['parsed_text'])
        self.assertIn("Snippet: Snippet for 2", results[1]['parsed_text'])
        mock_requests_get.assert_called_once()


    @patch('modules.clue_acquisition.acquirer.requests.get')
    def test_acquire_from_search_api_request_error(self, mock_requests_get):
        clue_acquisition_config.ACQUISITION_MODE = "search_api"
        clue_acquisition_config.SEARCH_API_ENDPOINT = "http://fakeapi.com/search"
        self.acquirer = ClueAcquirer() # Re-init

        mock_requests_get.side_effect = requests.exceptions.RequestException("Network error")

        search_params = {'search_terms': "test query"}
        results = self.acquirer.acquire_clues(search_params=search_params)

        self.assertEqual(len(results), 1)
        self.assertIn("Search API request failed: Network error", results[0].get("error", ""))

    def test_invalid_mode(self):
        clue_acquisition_config.ACQUISITION_MODE = "invalid_mode"
        self.acquirer = ClueAcquirer() # Re-init
        results = self.acquirer.acquire_clues()
        self.assertEqual(len(results), 1)
        self.assertIn("Invalid acquisition mode: invalid_mode", results[0].get("error", ""))

if __name__ == '__main__':
    unittest.main()
