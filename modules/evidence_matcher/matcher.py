# modules/evidence_matcher/matcher.py
import os
import json
import time
import requests # Using requests for broader compatibility if we switch from openai lib

# Attempt to import configurations
try:
    from config import main_config
    from config import evidence_matcher_config
except ImportError as e:
    print(f"WARN: EvidenceMatcher: Error importing configs: {e}. Using fallback defaults.")
    class main_config: #type: ignore
        OPENAI_API_KEY = "YOUR_FALLBACK_OPENAI_KEY" # Needs to be a valid key for actual calls
        LLM_BASE_URL = None
        SIMULATE_LLM = True # Critical for fallback

    class evidence_matcher_config: #type: ignore
        LLM_PROVIDER = "openai"
        EVIDENCE_MATCHING_MODEL_NAME = "fallback-model"
        LLM_TEMPERATURE = 0.2
        LLM_MAX_TOKENS = 1500
        PATENT_SUMMARY_PROMPT_PATH = "prompts/evidence_matcher/patent_summary_prompt.txt"
        INFRINGEMENT_ANALYSIS_PROMPT_PATH = "prompts/evidence_matcher/infringement_analysis_prompt.txt"

class EvidenceMatcher:
    def __init__(self):
        self.api_key = getattr(main_config, 'OPENAI_API_KEY', None)
        self.base_url = getattr(main_config, 'LLM_BASE_URL', None) # For custom OpenAI-compatible endpoints

        self.provider = evidence_matcher_config.LLM_PROVIDER
        self.model_name = evidence_matcher_config.EVIDENCE_MATCHING_MODEL_NAME
        self.temperature = evidence_matcher_config.LLM_TEMPERATURE
        self.max_tokens = evidence_matcher_config.LLM_MAX_TOKENS

        self.simulate_llm = getattr(main_config, 'SIMULATE_LLM', True)
        self.simulation_delay = getattr(main_config, 'SIMULATE_LLM_DELAY', 2)


        # Load prompts
        self.patent_summary_prompt_template = self._load_prompt_template(evidence_matcher_config.PATENT_SUMMARY_PROMPT_PATH)
        self.infringement_analysis_prompt_template = self._load_prompt_template(evidence_matcher_config.INFRINGEMENT_ANALYSIS_PROMPT_PATH)

        if not self.api_key or self.api_key == "YOUR_FALLBACK_OPENAI_KEY" or self.api_key == "sk-YOUR_OPENAI_API_KEY_HERE":
            print("WARN: EvidenceMatcher: OpenAI API key not configured or is a placeholder. Real LLM calls will fail unless SIMULATE_LLM is True.")
            if not self.simulate_llm:
                 print("ERROR: EvidenceMatcher: SIMULATE_LLM is False, but API key is missing/invalid. LLM calls will fail.")

        print(f"INFO: EvidenceMatcher initialized. LLM Provider: {self.provider}, Model: {self.model_name}, Simulate: {self.simulate_llm}")

    def _load_prompt_template(self, template_path):
        try:
            # Try to read relative to the project root or current working directory
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Assuming project root is two levels up from modules/evidence_matcher
            full_path = os.path.join(base_path, template_path)
            if not os.path.exists(full_path): # Fallback to path relative to cwd if not found from project root
                full_path = template_path
                if not os.path.exists(full_path):
                    raise FileNotFoundError(f"Prompt template not found at '{template_path}' (tried from project root and CWD)")

            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError as e:
            print(f"ERROR: EvidenceMatcher: Could not load prompt template: {e}")
            # Return a fallback prompt or raise error, depending on desired robustness
            return f"ERROR: Prompt template '{template_path}' not found. Please check configuration. Details: {e}"
        except Exception as e:
            print(f"ERROR: EvidenceMatcher: Unexpected error loading prompt template {template_path}: {e}")
            return f"ERROR: Unexpected error loading prompt template '{template_path}'. Details: {e}"

    def _call_llm(self, prompt_text, expect_json=True):
        """
        Helper function to call the configured LLM.
        Uses OpenAI-compatible API structure.
        """
        if self.simulate_llm:
            print(f"INFO: EvidenceMatcher: SIMULATING LLM call. Prompt (first 100 chars): {prompt_text[:100]}...")
            time.sleep(self.simulation_delay)
            # Simulate JSON response structure based on prompt type (very basic)
            if "patent_summary_prompt.txt" in prompt_text or "\"patent_title\"" in prompt_text : # Heuristic
                return {
                    "patent_title": "Simulated Patent X123",
                    "publication_number": "US-SIM-123",
                    "assignee": "SimuCorp",
                    "priority_date": "2023-01-01",
                    "technical_field": "Simulated Technology",
                    "problem_solved": "A simulated problem.",
                    "solution_summary": "A simulated solution.",
                    "key_claims_verbatim": ["Simulated Claim 1: A device comprising A and B.", "Simulated Claim 2: A method of doing C."],
                    "novelty_points": ["Simulated novelty A.", "Simulated novelty B."],
                    "main_components_or_steps": ["Component SimA", "Step Sim1"]
                }
            elif "infringement_analysis_prompt.txt" in prompt_text or "\"clue_identifier\"" in prompt_text: # Heuristic
                return {
                    "clue_identifier": "simulated_clue_id",
                    "patent_title_analyzed": "Simulated Patent X123",
                    "overall_infringement_risk_score": 75,
                    "literal_infringement_likelihood": "Medium",
                    "doctrine_of_equivalents_likelihood": "Low",
                    "key_evidence_features": ["Evidence Feature SimX", "Evidence Feature SimY"],
                    "claim_comparison": [{
                        "claim_number": "Claim 1",
                        "claim_text_snippet": "A device comprising A and B...",
                        "elements_mapping": [{"patent_element": "A", "evidence_mapping_status": "Found", "evidence_support_snippet": "Evidence mentions A-like part."}],
                        "overall_claim_match_status": "Some Elements Found"
                    }],
                    "reasoning_summary": "Simulated analysis suggests medium risk due to partial feature overlap.",
                    "strengths_of_infringement_case": ["Partial overlap of feature A."],
                    "weaknesses_of_infringement_case_or_potential_defenses": ["Feature B seems missing."]
                }
            return {"simulated_response": "This is a generic simulated LLM response."} if expect_json else "Generic simulated LLM text."

        if not self.api_key or self.api_key == "YOUR_FALLBACK_OPENAI_KEY" or self.api_key == "sk-YOUR_OPENAI_API_KEY_HERE":
            error_msg = "LLM API key is not configured or is a placeholder."
            print(f"ERROR: EvidenceMatcher: {error_msg}")
            if expect_json: return {"error": error_msg, "details": "API key missing."}
            return f"[LLM_ERROR: {error_msg}]"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        if expect_json:
            # For OpenAI, if you want to enforce JSON output (for newer models like gpt-3.5-turbo-1106+):
            # payload["response_format"] = {"type": "json_object"}
            # Check model compatibility before enabling this. For older models, rely on prompt engineering.
            # The prompts are already asking for JSON, which is a good first step.
            pass


        api_url_to_use = self.base_url if self.base_url else f"https://api.openai.com/v1/chat/completions"
        if self.provider == "deepseek" and not self.base_url: # Example for DeepSeek default if not using custom base_url
             api_url_to_use = "https://api.deepseek.com/chat/completions"


        try:
            print(f"INFO: EvidenceMatcher: Sending request to LLM. Endpoint: {api_url_to_use}, Model: {self.model_name}")
            response = requests.post(api_url_to_use, headers=headers, json=payload, timeout=120) # 120s timeout
            response.raise_for_status()  # Raise an exception for HTTP errors

            response_data = response.json()
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

            if expect_json:
                try:
                    # The content itself should be the JSON string if prompt is good
                    json_content = json.loads(content)
                    return json_content
                except json.JSONDecodeError as e:
                    error_msg = f"LLM response was not valid JSON. Error: {e}. Response text: {content[:500]}..."
                    print(f"ERROR: EvidenceMatcher: {error_msg}")
                    return {"error": "LLM_JSON_DECODE_ERROR", "details": error_msg, "raw_content": content}
            else:
                return content

        except requests.exceptions.RequestException as e:
            error_msg = f"LLM API request failed: {e}"
            print(f"ERROR: EvidenceMatcher: {error_msg}")
            if expect_json: return {"error": "LLM_REQUEST_ERROR", "details": str(e)}
            return f"[LLM_ERROR: {error_msg}]"
        except Exception as e: # Catch-all for other unexpected errors
            error_msg = f"Unexpected error during LLM call: {e}"
            print(f"ERROR: EvidenceMatcher: {error_msg}")
            if expect_json: return {"error": "LLM_UNEXPECTED_ERROR", "details": str(e)}
            return f"[LLM_ERROR: {error_msg}]"

    def summarize_patent_with_llm(self, patent_full_text):
        """
        Uses LLM to extract a structured summary from raw patent text.
        Args:
            patent_full_text (str): The full text of the patent.
        Returns:
            dict: A dictionary containing the structured patent summary, or an error dict.
        """
        if "ERROR: Prompt template" in self.patent_summary_prompt_template:
             return {"error": "Patent summary prompt template not loaded.", "details": self.patent_summary_prompt_template}

        prompt = self.patent_summary_prompt_template.format(patent_full_text=patent_full_text)

        print(f"INFO: EvidenceMatcher: Requesting patent summary from LLM for patent (text length: {len(patent_full_text)}).")
        # Assuming the patent text fits within context window or LLM handles it.
        # For very long texts, chunking and iterative summarization might be needed (more complex).

        summary_data = self._call_llm(prompt, expect_json=True)
        return summary_data

    def match_evidence(self, patent_summary_data, clue_text, clue_identifier="N/A"):
        """
        Compares a piece of evidence text against structured patent information using an LLM.
        Args:
            patent_summary_data (dict): Structured data about the patent (e.g., from summarize_patent_with_llm or other source).
                                        Expected keys: "patent_title", "technical_field",
                                                       "key_claims_verbatim" (list),
                                                       "novelty_points" (list),
                                                       "main_components_or_steps" (list).
            clue_text (str): The text content of the infringement clue.
            clue_identifier (str): A unique identifier for the clue (e.g., filename, URL).
        Returns:
            dict: A dictionary containing the structured infringement analysis, or an error dict.
        """
        if "ERROR: Prompt template" in self.infringement_analysis_prompt_template:
            return {"error": "Infringement analysis prompt template not loaded.", "details": self.infringement_analysis_prompt_template}

        # Ensure required patent data fields are present
        required_fields = ["patent_title", "technical_field", "key_claims_verbatim", "key_novelty_points", "main_components_or_steps"]
        missing_fields = [field for field in required_fields if field not in patent_summary_data or not patent_summary_data[field]]

        if missing_fields:
            error_msg = f"Missing required fields in patent_summary_data for matching: {', '.join(missing_fields)}"
            print(f"ERROR: EvidenceMatcher: {error_msg}")
            return {"error": "MISSING_PATENT_DATA_FIELDS", "details": error_msg, "clue_identifier": clue_identifier}

        prompt = self.infringement_analysis_prompt_template.format(
            patent_title=patent_summary_data.get("patent_title", "N/A"),
            technical_field=patent_summary_data.get("technical_field", "N/A"),
            core_claims_verbatim="\n".join([f"- {claim}" for claim in patent_summary_data.get("key_claims_verbatim", [])]),
            key_novelty_points="\n".join([f"- {point}" for point in patent_summary_data.get("key_novelty_points", [])]),
            main_components_or_steps="\n".join([f"- {comp}" for comp in patent_summary_data.get("main_components_or_steps", [])]),
            target_evidence_text=clue_text,
            clue_identifier=clue_identifier
        )

        print(f"INFO: EvidenceMatcher: Requesting infringement analysis from LLM for clue '{clue_identifier}' (text length: {len(clue_text)}).")
        analysis_result = self._call_llm(prompt, expect_json=True)

        # Ensure clue_identifier is in the result if LLM didn't include it or if in simulation
        if isinstance(analysis_result, dict) and 'error' not in analysis_result:
            if self.simulate_llm and "simulated_clue_id" == analysis_result.get("clue_identifier"):
                analysis_result['clue_identifier'] = clue_identifier # Override simulated one
            elif 'clue_identifier' not in analysis_result:
                 analysis_result['clue_identifier'] = clue_identifier

        return analysis_result

if __name__ == '__main__':
    print("--- EvidenceMatcher Test ---")
    # For this test to run meaningfully with real LLM calls, ensure:
    # 1. config/main_config.py has valid OPENAI_API_KEY (or other provider's key)
    # 2. config/main_config.py has SIMULATE_LLM = False
    # 3. config/evidence_matcher_config.py is set up.
    # 4. Prompt files exist at the specified paths.

    matcher = EvidenceMatcher()

    # Test 1: Patent Summarization (if SIMULATE_LLM=False, this makes a real API call)
    print("\n--- Test 1: Patent Summarization ---")
    sample_patent_text = """
    This is a long text describing a new invention, the "HyperSprocket 9000".
    Publication Number: US 2025/0012345 A1. Assignee: FutureTech Inc. Priority Date: 2024-03-15.
    The technical field is advanced mechanical widgets. It solves the problem of slow sprocketing.
    The solution involves a novel gear assembly and a self-lubricating mechanism.
    Claim 1: A hypersprocket device, comprising: a main housing; a plurality of geared cogs within said housing;
    and a feedback control loop monitoring cog rotation speed.
    Claim 2: The device of claim 1, wherein the cogs are made of unobtainium.
    Novelty includes the use of unobtainium and the specific configuration of the feedback loop.
    Main components are housing, cogs, control loop.
    """
    patent_summary = matcher.summarize_patent_with_llm(sample_patent_text)
    print("Patent Summary Result:")
    print(json.dumps(patent_summary, indent=2, ensure_ascii=False))

    if isinstance(patent_summary, dict) and patent_summary.get("error"):
        print(f"Patent summarization failed, cannot proceed with match test using this summary: {patent_summary['error']}")
    else:
        # Test 2: Evidence Matching
        print("\n--- Test 2: Evidence Matching ---")
        sample_clue_text = """
        A recent product teardown of the "WidgetMax 500" by RivalCorp revealed several interesting features.
        It has a primary casing, multiple spinning gears, and a sensor system that adjusts gear speed.
        The gears appear to be standard steel. The sensor system is quite advanced.
        """
        clue_id = "RivalCorp_WidgetMax500_Teardown.txt"

        # Use the summary from Test 1 (or a fallback if it failed but we still want to test matching prompt)
        if not patent_summary or patent_summary.get("error"):
             print("WARN: Using fallback patent summary for matching test as LLM summarization failed or was skipped.")
             patent_summary_for_match = { # Fallback if summary failed
                "patent_title": "HyperSprocket 9000 (Fallback)",
                "technical_field": "Advanced mechanical widgets (Fallback)",
                "key_claims_verbatim": ["Claim 1: A hypersprocket device, comprising: a main housing; a plurality of geared cogs within said housing; and a feedback control loop monitoring cog rotation speed."],
                "key_novelty_points": ["Use of unobtainium (not in evidence)", "Specific feedback loop configuration (similar in evidence)"],
                "main_components_or_steps": ["Main housing", "Geared cogs", "Feedback control loop"]
            }
        else:
            patent_summary_for_match = patent_summary


        match_result = matcher.match_evidence(patent_summary_for_match, sample_clue_text, clue_identifier=clue_id)
        print("\nEvidence Match Result:")
        print(json.dumps(match_result, indent=2, ensure_ascii=False))

    print("\n--- EvidenceMatcher Test Complete ---")
