# modules/reliability_assessor/assessor.py
import os
import json
import time
import requests # Using requests for broader compatibility

# Attempt to import configurations
try:
    from config import main_config
    from config import reliability_assessor_config
    # It might also need to know about evidence_matcher_config if rules depend on its output structure
except ImportError as e:
    print(f"WARN: ReliabilityAssessor: Error importing configs: {e}. Using fallback defaults.")
    class main_config: #type: ignore
        OPENAI_API_KEY = "YOUR_FALLBACK_OPENAI_KEY"
        LLM_BASE_URL = None
        SIMULATE_LLM = True

    class reliability_assessor_config: #type: ignore
        ASSESSOR_ENABLED = False
        ASSESSMENT_METHOD = "llm" # "llm", "rules_based", "hybrid"
        ASSESSMENT_MODEL_NAME = "fallback-assessor-model"
        ASSESSMENT_LLM_TEMPERATURE = 0.1
        ASSESSMENT_LLM_MAX_TOKENS = 800
        RELIABILITY_ASSESSMENT_PROMPT_PATH = "prompts/reliability_assessor/assessment_prompt.txt"
        # RULES_FILE_PATH = "config/fallback_reliability_rules.yaml"
        # LLM_SCORE_WEIGHT = 0.7
        # RULES_SCORE_WEIGHT = 0.3


class ReliabilityAssessor:
    def __init__(self):
        self.enabled = reliability_assessor_config.ASSESSOR_ENABLED
        self.method = reliability_assessor_config.ASSESSMENT_METHOD if self.enabled else None

        self.simulate_llm = getattr(main_config, 'SIMULATE_LLM', True)
        self.simulation_delay = getattr(main_config, 'SIMULATE_LLM_DELAY', 1)

        if self.enabled:
            print(f"INFO: ReliabilityAssessor initialized. Enabled: True, Method: {self.method}")
            if self.method in ["llm", "hybrid"]:
                self.api_key = getattr(main_config, 'OPENAI_API_KEY', None) # Or a specific key for this module
                self.base_url = getattr(main_config, 'LLM_BASE_URL', None) # Or specific base_url
                self.model_name = reliability_assessor_config.ASSESSMENT_MODEL_NAME
                self.temperature = reliability_assessor_config.ASSESSMENT_LLM_TEMPERATURE
                self.max_tokens = reliability_assessor_config.ASSESSMENT_LLM_MAX_TOKENS
                self.assessment_prompt_template = self._load_prompt_template(reliability_assessor_config.RELIABILITY_ASSESSMENT_PROMPT_PATH)

                if not self.api_key or self.api_key == "YOUR_FALLBACK_OPENAI_KEY" or self.api_key == "sk-YOUR_OPENAI_API_KEY_HERE":
                    print("WARN: ReliabilityAssessor: OpenAI API key not configured or is placeholder. Real LLM assessment calls will fail unless SIMULATE_LLM is True.")
                    if not self.simulate_llm and self.method == "llm":
                         print("ERROR: ReliabilityAssessor: SIMULATE_LLM is False, but API key is missing/invalid for LLM assessment. Calls will fail.")

            if self.method in ["rules_based", "hybrid"]:
                # self.rules = self._load_rules(reliability_assessor_config.RULES_FILE_PATH)
                print("INFO: ReliabilityAssessor: Rules-based assessment part initialized (rules loading placeholder).")
                pass # Placeholder for rule loading
        else:
            print("INFO: ReliabilityAssessor initialized. Enabled: False")

    def _load_prompt_template(self, template_path):
        try:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            full_path = os.path.join(base_path, template_path)
            if not os.path.exists(full_path):
                full_path = template_path # Fallback to CWD
                if not os.path.exists(full_path):
                    raise FileNotFoundError(f"Prompt template not found at '{template_path}'")
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"ERROR: ReliabilityAssessor: Could not load prompt template {template_path}: {e}")
            return f"ERROR: Prompt template '{template_path}' not loaded."

    def _load_rules(self, rules_path):
        # Placeholder for loading rules from a YAML or JSON file
        print(f"INFO: ReliabilityAssessor: Attempting to load rules from {rules_path} (placeholder).")
        return {"example_rule": "value"}

    def _call_llm_assessor(self, prompt_text):
        # This is similar to EvidenceMatcher._call_llm, can be refactored into a shared utility if desired
        if self.simulate_llm:
            print(f"INFO: ReliabilityAssessor: SIMULATING LLM assessment call. Prompt (first 100 chars): {prompt_text[:100]}...")
            time.sleep(self.simulation_delay)
            return {
                "assessed_clue_identifier": "simulated_clue_id_from_assessment",
                "reliability_score_of_previous_analysis": 85,
                "assessment_summary": "Simulated: The previous analysis appears mostly reliable with clear reasoning for its score.",
                "points_of_concern_in_previous_analysis": ["Simulated: Evidence snippet for one claim element was a bit brief."],
                "points_of_strength_in_previous_analysis": ["Simulated: Overall claim mapping was logical."]
            }

        if not self.api_key or self.api_key == "YOUR_FALLBACK_OPENAI_KEY" or self.api_key == "sk-YOUR_OPENAI_API_KEY_HERE":
            return {"error": "LLM_ASSESSMENT_API_KEY_MISSING", "details": "API key for reliability assessor not configured."}

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model_name, "messages": [{"role": "user", "content": prompt_text}],
            "temperature": self.temperature, "max_tokens": self.max_tokens
        }
        # if self.model_name includes "gpt-3.5-turbo-1106" or similar, can add: payload["response_format"] = {"type": "json_object"}

        api_url_to_use = self.base_url if self.base_url else f"https://api.openai.com/v1/chat/completions"
        # Add provider-specific default URLs if needed (e.g., for DeepSeek)
        # if self.provider == "deepseek" and not self.base_url: api_url_to_use = "https://api.deepseek.com/chat/completions"

        try:
            print(f"INFO: ReliabilityAssessor: Sending request to LLM for assessment. Endpoint: {api_url_to_use}, Model: {self.model_name}")
            response = requests.post(api_url_to_use, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            response_data = response.json()
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                return {"error": "LLM_ASSESSMENT_JSON_DECODE_ERROR", "details": str(e), "raw_content": content}
        except requests.exceptions.RequestException as e:
            return {"error": "LLM_ASSESSMENT_REQUEST_ERROR", "details": str(e)}
        except Exception as e:
            return {"error": "LLM_ASSESSMENT_UNEXPECTED_ERROR", "details": str(e)}

    def _assess_with_llm(self, evidence_match_data):
        if "ERROR: Prompt template" in self.assessment_prompt_template:
             return {"error": "Reliability assessment prompt template not loaded.", "details": self.assessment_prompt_template}

        previous_analysis_json_str_for_prompt = json.dumps(evidence_match_data, indent=2, ensure_ascii=False)
        prompt = self.assessment_prompt_template.format(
            previous_analysis_json=previous_analysis_json_str_for_prompt, # Corrected variable name
            clue_identifier_from_previous_analysis=evidence_match_data.get("clue_identifier", "N/A")
        )

        print(f"INFO: ReliabilityAssessor: Requesting LLM-based reliability assessment for clue '{evidence_match_data.get('clue_identifier', 'N/A')}'.")
        assessment_result = self._call_llm_assessor(prompt)
        return assessment_result

    def _assess_with_rules(self, evidence_match_data):
        print(f"INFO: ReliabilityAssessor: Performing rules-based reliability assessment for clue '{evidence_match_data.get('clue_identifier', 'N/A')}' (placeholder).")
        # Placeholder logic for rules-based assessment
        score = 70 # Default score
        concerns = []
        strengths = []
        summary = "Rules-based assessment (placeholder): "

        risk_score = evidence_match_data.get("overall_infringement_risk_score", 0)
        if risk_score < 30:
            score -= 10
            strengths.append("Low infringement risk score suggests clearer non-infringement.")
        elif risk_score > 70:
            score +=5 # High risk might be well-justified
            strengths.append("High infringement risk score, if well-justified by evidence, is a strong indicator.")

        if not evidence_match_data.get("reasoning_summary","").strip():
            score -=15
            concerns.append("Reasoning summary from previous analysis is empty or very short.")

        summary += f"Calculated score {score} based on predefined rules."
        return {
            "assessed_clue_identifier": evidence_match_data.get("clue_identifier", "N/A"),
            "reliability_score_of_previous_analysis": score,
            "assessment_summary": summary,
            "points_of_concern_in_previous_analysis": concerns,
            "points_of_strength_in_previous_analysis": strengths,
            "assessment_method_used": "rules_based_placeholder"
        }

    def _assess_with_hybrid(self, evidence_match_data):
        print(f"INFO: ReliabilityAssessor: Performing hybrid reliability assessment for clue '{evidence_match_data.get('clue_identifier', 'N/A')}' (placeholder).")
        llm_assessment = self._assess_with_llm(evidence_match_data)
        rules_assessment = self._assess_with_rules(evidence_match_data)

        # Combine scores (example logic)
        llm_score = llm_assessment.get("reliability_score_of_previous_analysis", 50) if not llm_assessment.get("error") else 50
        rules_score = rules_assessment.get("reliability_score_of_previous_analysis", 50)

        # llm_weight = reliability_assessor_config.LLM_SCORE_WEIGHT
        # rules_weight = reliability_assessor_config.RULES_SCORE_WEIGHT
        # final_score = int((llm_score * llm_weight) + (rules_score * rules_weight))
        final_score = int((llm_score * 0.7) + (rules_score * 0.3)) # Fallback weights

        return {
            "assessed_clue_identifier": evidence_match_data.get("clue_identifier", "N/A"),
            "reliability_score_of_previous_analysis": final_score,
            "assessment_summary": f"Hybrid assessment. LLM part: {llm_assessment.get('assessment_summary','N/A')}. Rules part: {rules_assessment.get('assessment_summary','N/A')}",
            "points_of_concern_in_previous_analysis": llm_assessment.get("points_of_concern_in_previous_analysis", []) + rules_assessment.get("points_of_concern_in_previous_analysis", []),
            "points_of_strength_in_previous_analysis": llm_assessment.get("points_of_strength_in_previous_analysis", []) + rules_assessment.get("points_of_strength_in_previous_analysis", []),
            "llm_assessment_details": llm_assessment, # Optional: include full sub-assessments
            "rules_assessment_details": rules_assessment, # Optional
            "assessment_method_used": "hybrid_placeholder"
        }

    def assess_reliability(self, evidence_match_data):
        """
        Assesses the reliability of the provided evidence match data.
        Args:
            evidence_match_data (dict): The output from the EvidenceMatcher module.
        Returns:
            dict: The evidence_match_data dictionary, potentially augmented with
                  reliability assessment fields (e.g., 'reliability_assessment').
                  If assessor is disabled, returns data with 'reliability_assessment_status': 'disabled'.
        """
        if not self.enabled:
            evidence_match_data['reliability_assessment'] = {
                "status": "disabled",
                "message": "Reliability assessor is not enabled in configuration."
            }
            return evidence_match_data

        print(f"INFO: ReliabilityAssessor: Assessing reliability for clue: {evidence_match_data.get('clue_identifier', 'N/A')}")

        assessment_output = None
        if self.method == "llm":
            assessment_output = self._assess_with_llm(evidence_match_data)
        elif self.method == "rules_based":
            assessment_output = self._assess_with_rules(evidence_match_data)
        elif self.method == "hybrid":
            assessment_output = self._assess_with_hybrid(evidence_match_data)
        else:
            assessment_output = {"error": "INVALID_ASSESSMENT_METHOD", "details": f"Configured method '{self.method}' is not supported."}
            print(f"ERROR: ReliabilityAssessor: Invalid assessment method '{self.method}'.")

        evidence_match_data['reliability_assessment'] = assessment_output
        return evidence_match_data

if __name__ == '__main__':
    print("--- ReliabilityAssessor Test ---")
    # For this test to run meaningfully with real LLM calls, ensure:
    # 1. config/main_config.py has valid OPENAI_API_KEY and SIMULATE_LLM = False
    # 2. config/reliability_assessor_config.py is set up with ASSESSOR_ENABLED = True
    #    and valid LLM/Rules settings.

    # Sample output from EvidenceMatcher
    sample_match_data = {
        "clue_identifier": "test_clue_001",
        "patent_title_analyzed": "Sample Patent Alpha",
        "overall_infringement_risk_score": 65,
        "literal_infringement_likelihood": "Low",
        "doctrine_of_equivalents_likelihood": "Medium",
        "key_evidence_features": ["Feature X (modified)", "Feature Y (present)"],
        "claim_comparison": [{
            "claim_number": "Claim 1",
            "claim_text_snippet": "A widget comprising X, Y, and Z...",
            "elements_mapping": [
                {"patent_element": "X", "evidence_mapping_status": "Found Equivalently", "evidence_support_snippet": "Evidence shows X' which is similar to X."},
                {"patent_element": "Y", "evidence_mapping_status": "Found", "evidence_support_snippet": "Evidence clearly describes Y."},
                {"patent_element": "Z", "evidence_mapping_status": "Not Found", "evidence_support_snippet": "Z is not mentioned in evidence."}
            ],
            "overall_claim_match_status": "Some Elements Missing"
        }],
        "reasoning_summary": "Medium risk due to presence of Y and equivalent X, but Z is missing. Equivalence for X needs careful review.",
        "strengths_of_infringement_case": ["Y is clearly present.", "X' could be equivalent to X."],
        "weaknesses_of_infringement_case_or_potential_defenses": ["Element Z is missing, which might break literal infringement.", "Difference between X and X' needs justification for equivalence."]
    }

    # --- Test 1: Assessor Disabled (default if config not changed) ---
    print("\n--- Test 1: Assessor Disabled ---")
    # To ensure it's disabled for this test, we can manually set it if needed,
    # or rely on the default reliability_assessor_config.ASSESSOR_ENABLED = False
    # Forcing it for this test section:
    original_enabled_state = reliability_assessor_config.ASSESSOR_ENABLED
    reliability_assessor_config.ASSESSOR_ENABLED = False
    assessor_disabled = ReliabilityAssessor()
    result_disabled = assessor_disabled.assess_reliability(sample_match_data.copy())
    print("Result (Assessor Disabled):")
    print(json.dumps(result_disabled.get('reliability_assessment'), indent=2, ensure_ascii=False))
    reliability_assessor_config.ASSESSOR_ENABLED = original_enabled_state # Restore

    # --- Test 2: Assessor Enabled - LLM Mode ---
    print("\n--- Test 2: Assessor Enabled - LLM Mode ---")
    # Requires SIMULATE_LLM = False in main_config for real call, or will use simulation
    # Forcing enabled and LLM mode for this test section:
    original_enabled_state = reliability_assessor_config.ASSESSOR_ENABLED
    original_method_state = reliability_assessor_config.ASSESSMENT_METHOD
    reliability_assessor_config.ASSESSOR_ENABLED = True
    reliability_assessor_config.ASSESSMENT_METHOD = "llm"
    assessor_llm = ReliabilityAssessor() # Re-init to pick up changes
    result_llm = assessor_llm.assess_reliability(sample_match_data.copy())
    print("Result (LLM Mode):")
    print(json.dumps(result_llm.get('reliability_assessment'), indent=2, ensure_ascii=False))
    reliability_assessor_config.ASSESSOR_ENABLED = original_enabled_state # Restore
    reliability_assessor_config.ASSESSMENT_METHOD = original_method_state # Restore


    # --- Test 3: Assessor Enabled - Rules-Based Mode (Placeholder) ---
    print("\n--- Test 3: Assessor Enabled - Rules-Based Mode ---")
    original_enabled_state = reliability_assessor_config.ASSESSOR_ENABLED
    original_method_state = reliability_assessor_config.ASSESSMENT_METHOD
    reliability_assessor_config.ASSESSOR_ENABLED = True
    reliability_assessor_config.ASSESSMENT_METHOD = "rules_based"
    assessor_rules = ReliabilityAssessor()
    result_rules = assessor_rules.assess_reliability(sample_match_data.copy())
    print("Result (Rules-Based Mode):")
    print(json.dumps(result_rules.get('reliability_assessment'), indent=2, ensure_ascii=False))
    reliability_assessor_config.ASSESSOR_ENABLED = original_enabled_state
    reliability_assessor_config.ASSESSMENT_METHOD = original_method_state

    # --- Test 4: Assessor Enabled - Hybrid Mode (Placeholder) ---
    print("\n--- Test 4: Assessor Enabled - Hybrid Mode ---")
    original_enabled_state = reliability_assessor_config.ASSESSOR_ENABLED
    original_method_state = reliability_assessor_config.ASSESSMENT_METHOD
    reliability_assessor_config.ASSESSOR_ENABLED = True
    reliability_assessor_config.ASSESSMENT_METHOD = "hybrid"
    assessor_hybrid = ReliabilityAssessor()
    result_hybrid = assessor_hybrid.assess_reliability(sample_match_data.copy())
    print("Result (Hybrid Mode):")
    print(json.dumps(result_hybrid.get('reliability_assessment'), indent=2, ensure_ascii=False))
    reliability_assessor_config.ASSESSOR_ENABLED = original_enabled_state
    reliability_assessor_config.ASSESSMENT_METHOD = original_method_state

    print("\n--- ReliabilityAssessor Test Complete ---")
