import unittest
import os
import json
from unittest.mock import patch, MagicMock

from modules.reliability_assessor import ReliabilityAssessor
# Import configs to potentially modify them for testing
from config import main_config, reliability_assessor_config

class TestReliabilityAssessor(unittest.TestCase):

    def setUp(self):
        # Store original config values
        self.original_simulate_llm = main_config.SIMULATE_LLM
        self.original_api_key = main_config.OPENAI_API_KEY
        self.original_assessor_enabled = reliability_assessor_config.ASSESSOR_ENABLED
        self.original_assessment_method = reliability_assessor_config.ASSESSMENT_METHOD
        self.original_prompt_path = reliability_assessor_config.RELIABILITY_ASSESSMENT_PROMPT_PATH

        # Default to SIMULATE_LLM = True for most tests
        main_config.SIMULATE_LLM = True
        main_config.OPENAI_API_KEY = "dummy_key_for_assessor_tests"

        self.mock_assessment_prompt = "Assess this: {previous_analysis_json} for clue {clue_identifier_from_previous_analysis}"

        self.patcher_load_prompt = patch('modules.reliability_assessor.assessor.ReliabilityAssessor._load_prompt_template',
                                         return_value=self.mock_assessment_prompt)
        self.mock_load_template = self.patcher_load_prompt.start()

        self.sample_match_data = {
            "clue_identifier": "test_clue_001",
            "overall_infringement_risk_score": 65,
            "reasoning_summary": "Medium risk due to some overlap."
            # Add other fields as expected by the assessment prompt if necessary
        }

    def tearDown(self):
        self.patcher_load_prompt.stop()
        # Restore original config values
        main_config.SIMULATE_LLM = self.original_simulate_llm
        main_config.OPENAI_API_KEY = self.original_api_key
        reliability_assessor_config.ASSESSOR_ENABLED = self.original_assessor_enabled
        reliability_assessor_config.ASSESSMENT_METHOD = self.original_assessment_method
        reliability_assessor_config.RELIABILITY_ASSESSMENT_PROMPT_PATH = self.original_prompt_path

    def test_assessor_disabled(self):
        reliability_assessor_config.ASSESSOR_ENABLED = False
        assessor = ReliabilityAssessor() # Re-init

        result_data = assessor.assess_reliability(self.sample_match_data.copy())

        self.assertIn("reliability_assessment", result_data)
        self.assertEqual(result_data["reliability_assessment"]["status"], "disabled")

    def test_assess_with_llm_simulated(self):
        reliability_assessor_config.ASSESSOR_ENABLED = True
        reliability_assessor_config.ASSESSMENT_METHOD = "llm"
        main_config.SIMULATE_LLM = True # Ensure simulation is on
        assessor = ReliabilityAssessor() # Re-init

        result_data = assessor.assess_reliability(self.sample_match_data.copy())

        self.assertIn("reliability_assessment", result_data)
        assessment_output = result_data["reliability_assessment"]
        self.assertNotIn("error", assessment_output)
        self.assertEqual(assessment_output["assessed_clue_identifier"], "simulated_clue_id_from_assessment")
        self.assertEqual(assessment_output["reliability_score_of_previous_analysis"], 85) # From simulation logic

    def test_assess_with_rules_placeholder(self):
        reliability_assessor_config.ASSESSOR_ENABLED = True
        reliability_assessor_config.ASSESSMENT_METHOD = "rules_based"
        assessor = ReliabilityAssessor() # Re-init

        result_data = assessor.assess_reliability(self.sample_match_data.copy())

        self.assertIn("reliability_assessment", result_data)
        assessment_output = result_data["reliability_assessment"]
        self.assertNotIn("error", assessment_output)
        self.assertIn("reliability_score_of_previous_analysis", assessment_output)
        self.assertEqual(assessment_output["assessment_method_used"], "rules_based_placeholder")
        # Check a sample rule effect
        expected_score_based_on_sample_rules = 70 # Default
        if self.sample_match_data["overall_infringement_risk_score"] > 70: # 65 is not > 70
             expected_score_based_on_sample_rules += 5
        self.assertEqual(assessment_output["reliability_score_of_previous_analysis"], expected_score_based_on_sample_rules)


    def test_assess_with_hybrid_placeholder_simulated_llm(self):
        reliability_assessor_config.ASSESSOR_ENABLED = True
        reliability_assessor_config.ASSESSMENT_METHOD = "hybrid"
        main_config.SIMULATE_LLM = True # LLM part will be simulated
        assessor = ReliabilityAssessor() # Re-init

        result_data = assessor.assess_reliability(self.sample_match_data.copy())

        self.assertIn("reliability_assessment", result_data)
        assessment_output = result_data["reliability_assessment"]
        self.assertNotIn("error", assessment_output)
        self.assertIn("reliability_score_of_previous_analysis", assessment_output)
        self.assertEqual(assessment_output["assessment_method_used"], "hybrid_placeholder")

        # Check combined score (simulated LLM score 85, rules score 70 for sample_match_data)
        # Default weights 0.7 for LLM, 0.3 for rules
        expected_score = int((85 * 0.7) + (70 * 0.3))
        self.assertEqual(assessment_output["reliability_score_of_previous_analysis"], expected_score)

    @patch('modules.reliability_assessor.assessor.requests.post')
    def test_assess_with_llm_real_api_call(self, mock_post):
        reliability_assessor_config.ASSESSOR_ENABLED = True
        reliability_assessor_config.ASSESSMENT_METHOD = "llm"
        main_config.SIMULATE_LLM = False # Test real path
        assessor = ReliabilityAssessor() # Re-init

        mock_response = MagicMock()
        mock_response.status_code = 200
        expected_json_payload = {
            "assessed_clue_identifier": self.sample_match_data["clue_identifier"],
            "reliability_score_of_previous_analysis": 90,
            "assessment_summary": "Very reliable.",
            "points_of_concern_in_previous_analysis": [],
            "points_of_strength_in_previous_analysis": ["All good."]
        }
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(expected_json_payload)}}]
        }
        mock_post.return_value = mock_response

        result_data = assessor.assess_reliability(self.sample_match_data.copy())

        self.assertIn("reliability_assessment", result_data)
        assessment_output = result_data["reliability_assessment"]
        self.assertEqual(assessment_output, expected_json_payload)
        mock_post.assert_called_once()

if __name__ == '__main__':
    unittest.main()
