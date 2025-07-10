import unittest
import os
import json
from unittest.mock import patch, mock_open, MagicMock # Added MagicMock
import requests # Added requests

from modules.evidence_matcher import EvidenceMatcher
# Import configs to potentially modify them for testing
from config import main_config, evidence_matcher_config

class TestEvidenceMatcher(unittest.TestCase):

    def setUp(self):
        # Store original config values
        self.original_simulate_llm = main_config.SIMULATE_LLM
        self.original_api_key = main_config.OPENAI_API_KEY
        self.original_summary_prompt_path = evidence_matcher_config.PATENT_SUMMARY_PROMPT_PATH
        self.original_analysis_prompt_path = evidence_matcher_config.INFRINGEMENT_ANALYSIS_PROMPT_PATH

        # Default to SIMULATE_LLM = True for most tests to avoid actual API calls
        main_config.SIMULATE_LLM = True
        main_config.OPENAI_API_KEY = "dummy_key_for_tests" # Ensure it's not None for non-simulated path checks

        # Mock prompt file loading within EvidenceMatcher for controlled tests
        # We are testing the class logic, not the file loading itself here primarily
        self.mock_summary_prompt = "Summary prompt: {patent_full_text}"
        self.mock_analysis_prompt = "Analysis prompt: {patent_title} vs {target_evidence_text} for {clue_identifier}"

        # Patch _load_prompt_template for all tests in this class
        self.patcher1 = patch('modules.evidence_matcher.matcher.EvidenceMatcher._load_prompt_template',
                              side_effect=self._mocked_load_prompt_template)
        self.mock_load_template = self.patcher1.start()

        self.matcher = EvidenceMatcher()

    def tearDown(self):
        self.patcher1.stop()
        # Restore original config values
        main_config.SIMULATE_LLM = self.original_simulate_llm
        main_config.OPENAI_API_KEY = self.original_api_key
        evidence_matcher_config.PATENT_SUMMARY_PROMPT_PATH = self.original_summary_prompt_path
        evidence_matcher_config.INFRINGEMENT_ANALYSIS_PROMPT_PATH = self.original_analysis_prompt_path


    def _mocked_load_prompt_template(self, template_path):
        if template_path == evidence_matcher_config.PATENT_SUMMARY_PROMPT_PATH:
            # Include original path hint for better matching in _call_llm simulation
            return f"SimulatedPromptOrigin:{evidence_matcher_config.PATENT_SUMMARY_PROMPT_PATH}\n{self.mock_summary_prompt}"
        elif template_path == evidence_matcher_config.INFRINGEMENT_ANALYSIS_PROMPT_PATH:
            return f"SimulatedPromptOrigin:{evidence_matcher_config.INFRINGEMENT_ANALYSIS_PROMPT_PATH}\n{self.mock_analysis_prompt}"
        raise FileNotFoundError(f"Unexpected prompt path in mock: {template_path}")

    def test_summarize_patent_with_llm_simulated(self):
        main_config.SIMULATE_LLM = True
        self.matcher = EvidenceMatcher() # Re-init to pick up SIMULATE_LLM

        sample_patent_text = "This is a sample patent."
        result = self.matcher.summarize_patent_with_llm(sample_patent_text)

        self.assertIn("patent_title", result)
        self.assertEqual(result["patent_title"], "Simulated Patent X123") # Based on current simulation logic in EvidenceMatcher

    def test_match_evidence_simulated(self):
        main_config.SIMULATE_LLM = True
        self.matcher = EvidenceMatcher() # Re-init

        patent_summary_data = {
            "patent_title": "Test Patent", "technical_field": "Testing",
            "key_claims_verbatim": ["Claim 1: A testing apparatus."],
            "key_novelty_points": ["Novel test point."],
            "main_components_or_steps": ["Test component."]
        }
        clue_text = "This is a test clue."
        clue_identifier = "test_clue_01"

        result = self.matcher.match_evidence(patent_summary_data, clue_text, clue_identifier)

        self.assertIn("clue_identifier", result)
        # After fix, the passed clue_identifier should be used even in simulation
        self.assertEqual(result["clue_identifier"], clue_identifier)
        self.assertIn("overall_infringement_risk_score", result)
        self.assertEqual(result["overall_infringement_risk_score"], 75) # Check simulation output

    def test_match_evidence_missing_patent_data(self):
        patent_summary_data = {"patent_title": "Test Patent"} # Missing other required fields
        clue_text = "This is a test clue."
        result = self.matcher.match_evidence(patent_summary_data, clue_text, "clue_id")
        self.assertIn("error", result)
        self.assertEqual(result["error"], "MISSING_PATENT_DATA_FIELDS")

    @patch('modules.evidence_matcher.matcher.requests.post')
    def test_call_llm_real_api_success_json(self, mock_post):
        main_config.SIMULATE_LLM = False # Test real path
        self.matcher = EvidenceMatcher() # Re-init

        mock_response = MagicMock()
        mock_response.status_code = 200
        # LLM actual response is a JSON string within the 'content' field
        expected_json_payload = {"key": "value", "text_analysis": "some analysis"}
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(expected_json_payload)}}]
        }
        mock_post.return_value = mock_response

        prompt = "Test prompt for JSON"
        result = self.matcher._call_llm(prompt, expect_json=True)

        self.assertEqual(result, expected_json_payload)
        mock_post.assert_called_once()
        # We can add more assertions here to check the structure of the POST request if needed

    @patch('modules.evidence_matcher.matcher.requests.post')
    def test_call_llm_real_api_failure_request_exception(self, mock_post):
        main_config.SIMULATE_LLM = False
        self.matcher = EvidenceMatcher()

        mock_post.side_effect = requests.exceptions.RequestException("Network Error")

        result = self.matcher._call_llm("Test prompt", expect_json=True)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "LLM_REQUEST_ERROR")
        self.assertIn("Network Error", result["details"])

    @patch('modules.evidence_matcher.matcher.requests.post')
    def test_call_llm_real_api_invalid_json_response(self, mock_post):
        main_config.SIMULATE_LLM = False
        self.matcher = EvidenceMatcher()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
             "choices": [{"message": {"content": "This is not valid JSON"}}]
        }
        mock_post.return_value = mock_response

        result = self.matcher._call_llm("Test prompt for invalid JSON", expect_json=True)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "LLM_JSON_DECODE_ERROR")
        self.assertIn("This is not valid JSON", result["raw_content"])

    def test_api_key_missing_for_real_call(self):
        main_config.SIMULATE_LLM = False
        original_api_key = main_config.OPENAI_API_KEY
        main_config.OPENAI_API_KEY = None # Simulate missing API key
        self.matcher = EvidenceMatcher() # Re-init with missing key

        result = self.matcher._call_llm("Test prompt", expect_json=True)
        self.assertIn("error", result)
        self.assertEqual(result["details"], "API key missing.")

        main_config.OPENAI_API_KEY = original_api_key # Restore


if __name__ == '__main__':
    unittest.main()
