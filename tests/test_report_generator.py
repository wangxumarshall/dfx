import unittest
import os
import datetime
from unittest.mock import patch, mock_open

from modules.report_generator import ReportGenerator
from config import report_generator_config # To check default paths or override

class TestReportGenerator(unittest.TestCase):

    def setUp(self):
        # Store original config values
        self.original_template_paths = {
            key: getattr(report_generator_config, key.upper() + "_TEMPLATE", None)
            for key in ["header", "patent_info", "summary_table", "evidence_detail", "reliability_info", "conclusion", "footer"]
        }
        self.original_disclaimer = report_generator_config.REPORT_DISCLAIMER

        # Mock all template file loading for isolated testing of formatting logic
        self.mock_templates = {
            "header": "# Report\nTime: {generation_time}, ID: {task_id}\n---\n",
            "patent_info": "## Patent Info\nTitle: {patent_title}\nClaims: {key_claims_verbatim}\nNovelty: {novelty_points}\n---\n",
            "summary_table": "## Summary Table\nTotal: {total_clues_analyzed}\n{summary_table_rows}\n---\n",
            "evidence_detail": "### Clue {clue_sequence_number}: {clue_identifier}\nScore: {overall_infringement_risk_score}\nReason: {reasoning_summary}\nClaims Compared:\n{claim_comparison_details}\n---",
            "reliability_info": "**Reliability**: Score: {reliability_score_of_previous_analysis}\nSummary: {assessment_summary}\n---",
            "conclusion": "## Conclusion\n{overall_conclusion_and_recommendation_text}\n---",
            "footer": "---\nDisclaimer: {report_disclaimer}"
        }

        self.patcher_load_templates = patch('modules.report_generator.generator.ReportGenerator._load_templates',
                                            return_value=self.mock_templates)
        self.mock_load = self.patcher_load_templates.start()

        self.generator = ReportGenerator()

        # Sample data for report generation
        self.sample_patent_data = {
            "patent_title": "Test Patent Alpha", "publication_number": "P123", "assignee": "TestCorp", "priority_date": "2023-01-01",
            "technical_field": "Testing", "problem_solved": "Test problem", "solution_summary": "Test solution",
            "key_claims_verbatim": ["Claim 1: A method.", "Claim 2: A device."],
            "novelty_points": ["Novelty A", "Novelty B"],
            "main_components_or_steps": ["Step 1", "Component X"],
            "overall_conclusion_and_recommendation_text": "This is a test conclusion."
        }
        self.sample_evidence_analyses = [
            {
                "clue_identifier": "clue_A.pdf", "overall_infringement_risk_score": 70,
                "literal_infringement_likelihood": "Medium", "doctrine_of_equivalents_likelihood": "Low",
                "reasoning_summary": "Reason A", "key_evidence_features": ["Feat1", "Feat2"],
                "claim_comparison": [{"claim_number": "1", "claim_text_snippet":"A method..", "elements_mapping": [], "overall_claim_match_status": "Some Elements Missing"}],
                "strengths_of_infringement_case": ["Strength A"], "weaknesses_of_infringement_case_or_potential_defenses": ["Weakness A"],
                "reliability_assessment": {"reliability_score_of_previous_analysis": 80, "assessment_summary": "Reliable A"}
            },
            {
                "clue_identifier": "clue_B.txt", "overall_infringement_risk_score": 40,
                "literal_infringement_likelihood": "Low", "doctrine_of_equivalents_likelihood": "None",
                "reasoning_summary": "Reason B", "key_evidence_features": ["Feat3"],
                "claim_comparison": [],
                "strengths_of_infringement_case": [], "weaknesses_of_infringement_case_or_potential_defenses": ["Weakness B"],
                "reliability_assessment": {"status": "disabled", "message": "Assessor disabled for B"}
            }
        ]
        self.sample_metadata = {"task_id": "TASK001", "generation_time": "2024-01-01 12:00:00"}


    def tearDown(self):
        self.patcher_load_templates.stop()
        # Restore original config values
        report_generator_config.REPORT_DISCLAIMER = self.original_disclaimer
        for key, path in self.original_template_paths.items():
            if path is not None: # Check if it was originally set
                 setattr(report_generator_config, key.upper() + "_TEMPLATE", path)
            # If it wasn't set and we added it during test, it might need delattr, but this setup avoids that.


    def test_generate_report_structure(self):
        report = self.generator.generate_report(self.sample_patent_data, self.sample_evidence_analyses, self.sample_metadata)

        # Check for presence of key sections based on mocked templates
        self.assertIn("# Report", report) # Header
        self.assertIn("Time: 2024-01-01 12:00:00", report)
        self.assertIn("ID: TASK001", report)

        self.assertIn("## Patent Info", report) # Patent Info
        self.assertIn("Title: Test Patent Alpha", report)
        self.assertIn("- Claim 1: A method.\n- Claim 2: A device.", report)
        self.assertIn("- Novelty A\n- Novelty B", report) # Corrected: no extra indent for second novelty point

        self.assertIn("## Summary Table", report) # Summary Table
        self.assertIn("Total: 2", report)
        # Check for table rows (simplified check for identifiers)
        self.assertIn("| clue_A.pdf ", report)
        self.assertIn("| 70 ", report) # Risk score for A
        self.assertIn("| 80 |", report) # Reliability for A
        self.assertIn("| clue_B.txt ", report)
        self.assertIn("| 40 ", report) # Risk score for B
        self.assertIn("| N/A (Disabled) |", report) # Reliability for B

        self.assertIn("### Clue 2.1.1: clue_A.pdf", report) # Evidence Detail A
        self.assertIn("Score: 70", report)
        self.assertIn("Reason: Reason A", report)
        self.assertIn("**Reliability**: Score: 80", report) # Reliability for A

        self.assertIn("### Clue 2.1.2: clue_B.txt", report) # Evidence Detail B
        self.assertIn("Score: 40", report)
        self.assertIn("**可靠性评估**: Assessor disabled for B", report) # Reliability disabled message for B

        self.assertIn("## Conclusion", report) # Conclusion
        self.assertIn("This is a test conclusion.", report)

        self.assertIn("Disclaimer: " + report_generator_config.REPORT_DISCLAIMER, report) # Footer

    def test_format_list_to_md(self):
        self.assertEqual(self.generator._format_list_to_md(["item1", "item2"]), "- item1\n- item2")
        self.assertEqual(self.generator._format_list_to_md(["item1", "item2"], indent=1), "  - item1\n  - item2")
        self.assertEqual(self.generator._format_list_to_md([]), "N/A")
        self.assertEqual(self.generator._format_list_to_md(None), "None")


    def test_format_claim_comparison(self):
        claim_comp_data = [
            {"claim_number": "1", "claim_text_snippet":"Method A..",
             "elements_mapping": [
                 {"patent_element": "Elem1", "evidence_mapping_status": "Found", "evidence_support_snippet": "Found here."},
                 {"patent_element": "Elem2", "evidence_mapping_status": "Not Found", "evidence_support_snippet": "Missing."}
             ],
             "overall_claim_match_status": "Some Elements Missing"},
            {"claim_number": "5", "claim_text_snippet":"Device B..", "elements_mapping": [], "overall_claim_match_status": "No Elements Found"}
        ]
        formatted = self.generator._format_claim_comparison(claim_comp_data)
        self.assertIn("Claim 1", formatted)
        self.assertIn("Elem1", formatted)
        self.assertIn("Found here", formatted)
        self.assertIn("Elem2", formatted)
        self.assertIn("Missing", formatted)
        self.assertIn("Some Elements Missing", formatted)
        self.assertIn("Claim 5", formatted)
        self.assertIn("No Elements Found", formatted)
        self.assertEqual(self.generator._format_claim_comparison([]), "No claim comparison data provided.")

    def test_include_raw_llm_responses_config(self):
        report_generator_config.INCLUDE_RAW_LLM_RESPONSES = True
        self.generator = ReportGenerator() # Re-init

        report = self.generator.generate_report(self.sample_patent_data, self.sample_evidence_analyses, self.sample_metadata)
        self.assertIn("<details><summary>原始匹配分析JSON (点击展开)</summary>", report)

        report_generator_config.INCLUDE_RAW_LLM_RESPONSES = False # Reset
        self.generator = ReportGenerator() # Re-init
        report_no_raw = self.generator.generate_report(self.sample_patent_data, self.sample_evidence_analyses, self.sample_metadata)
        self.assertNotIn("<details><summary>原始匹配分析JSON (点击展开)</summary>", report_no_raw)


if __name__ == '__main__':
    unittest.main()
