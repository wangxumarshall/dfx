import time
import openai
import json
from .config import settings
from . import prompts

# Global LLM client
llm_client = None

def get_llm_client():
    """
    Initializes and returns a thread-safe LLM client based on the provider.
    """
    global llm_client
    if llm_client:
        return llm_client

    provider = settings.LLM_PROVIDER

    if provider == "openai":
        llm_client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
    elif provider == "deepseek":
        try:
            from deepseek import DeepSeek  # Assuming a library name
            llm_client = DeepSeek(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.LLM_BASE_URL
            )
        except ImportError:
            raise ImportError("DeepSeek library not found. Please install it via `pip install deepseek`.")
    elif provider == "ollama":
        # For Ollama, the client doesn't need an API key by default
        # The base_url is typically http://localhost:11434
        llm_client = openai.OpenAI(
            base_url=settings.LLM_BASE_URL or "http://localhost:11434/v1",
            api_key="ollama" # Required by the library, but not used by Ollama
        )
    elif provider == "none":
        llm_client = None
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    return llm_client


def get_llm_response(prompt, system_prompt=None, model_name=None, max_tokens=None, temperature=None, json_mode=False):
    """
    Generic function to get a response from the configured LLM.
    Handles different providers and simulation mode.
    """
    if settings.SIMULATE_LLM:
        return _simulate_llm_call(prompt, json_mode)

    client = get_llm_client()
    if not client:
        return "[LLM_ERROR: LLM provider is set to 'none' or not configured.]"

    model = model_name or settings.LLM_MODEL_NAME
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    request_params = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
        "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
    }

    if json_mode and settings.LLM_PROVIDER in ["openai", "ollama"]:
        request_params["response_format"] = {"type": "json_object"}

    try:
        print(f"Attempting LLM call to model: {model} (JSON Mode: {json_mode})")
        response = client.chat.completions.create(**request_params)
        content = response.choices[0].message.content.strip()

        if json_mode:
            # The 'json_object' mode should guarantee valid JSON, but we parse it here
            # to return a Python dict, which is more useful for the caller.
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                print(f"LLM API call failed: Model did not return valid JSON despite json_mode. Content:\n{content}")
                return f"[LLM_ERROR: Failed to parse JSON response from model.]"

        return content

    except Exception as e:
        print(f"LLM API call failed: {e}")
        return f"[LLM_ERROR: {e}]"


def _simulate_llm_call(prompt, json_mode=False):
    """Handles the simulation logic for LLM calls."""
    print(f"\n--- SIMULATING LLM CALL (JSON Mode: {json_mode}) ---")
    print(f"Model: {settings.LLM_MODEL_NAME}")
    print(f"Prompt (first 200 chars):\n{prompt[:200]}...\n")
    time.sleep(settings.SIMULATE_LLM_DELAY)

    # Performance analysis simulation
    if "identify performance bottlenecks" in prompt:
        if json_mode:
            return {
                "identified_bottlenecks": [
                    {
                        "function_stack": "main;read_file;process_data",
                        "percentage": 45.5,
                        "analysis": "This function is responsible for nearly half of the execution time. The `process_data` part seems to be computationally intensive.",
                        "optimization_suggestion": "Consider optimizing the `process_data` function. Possible improvements include using more efficient algorithms or parallelizing the workload."
                    },
                    {
                        "function_stack": "main;write_output;format_json",
                        "percentage": 22.1,
                        "analysis": "Significant time is spent formatting and writing the output file. This could be due to large data volumes or inefficient serialization.",
                        "optimization_suggestion": "Use a faster JSON library like orjson. If possible, stream the output instead of buffering it all in memory."
                    }
                ],
                "overall_summary": "The application is I/O bound, with major bottlenecks in data processing and output generation. Focusing on these two areas should yield significant performance improvements."
            }
        else:
            return """
### AI-Powered Analysis (Simulated)

**Top Bottleneck: `main;read_file;process_data` (45.5% of samples)**
*   **Analysis:** This function is responsible for nearly half of the execution time. The `process_data` part seems to be computationally intensive.
*   **Suggestion:** Consider optimizing the `process_data` function. Possible improvements include using more efficient algorithms or parallelizing the workload.

**Second Bottleneck: `main;write_output;format_json` (22.1% of samples)**
*   **Analysis:** Significant time is spent formatting and writing the output file. This could be due to large data volumes or inefficient serialization.
*   **Suggestion:** Use a faster JSON library like `orjson`. If possible, stream the output instead of buffering it all in memory.
"""

    # Fallback for other prompts
    return "This is a simulated LLM response."


def analyze_patent_text(patent_full_text):
    """
    Uses LLM to extract summary, key claims, and features from patent text.
    """
    prompt = prompt_templates.PATENT_SUMMARY_PROMPT.format(patent_text=patent_full_text)

    print(f"LLM Analyzer: Requesting patent summary and feature extraction for patent (text length: {len(patent_full_text)}).")
    # In a real scenario, you might need to chunk the text if it's too long for the LLM context window.
    # For now, assuming it fits or the LLM handles truncation/summarization of long inputs.

    response_text = get_llm_response(prompt, max_tokens=1000, temperature=0.1) # Lower temp for factual extraction

    # TODO: Parse the structured response from LLM (e.g., if it's markdown or JSON)
    # For now, assume it's a string that can be directly used or further processed by report_generator.
    # Example parsing (very basic, assumes the LLM follows the format):
    parsed_data = {"raw_response": response_text}
    try:
        lines = response_text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("**专利名称**："):
                parsed_data["patent_name"] = line.replace("**专利名称**：", "").strip()
            elif line.startswith("**技术领域**："):
                parsed_data["technical_field"] = line.replace("**技术领域**：", "").strip()
            elif line.startswith("**核心权利要求**："):
                claims = []
                for claim_line in lines[i+1:]:
                    if claim_line.startswith("1.") or claim_line.startswith("- ") or not claim_line.strip().startswith("**"): # simple claim line detection
                         if claim_line.strip() and not claim_line.startswith("**主要技术特点/创新点**："):
                            claims.append(claim_line.strip())
                         else: # Stop if next section starts or empty line
                            break
                    elif claim_line.startswith("**主要技术特点/创新点**："): # Reached next section
                        break
                parsed_data["core_claims"] = "\n".join(claims)
            elif line.startswith("**主要技术特点/创新点**："):
                features = []
                for feature_line in lines[i+1:]:
                    if feature_line.startswith("- ") or (feature_line.strip() and not feature_line.startswith("**")):
                        features.append(feature_line.strip())
                    else:
                        break
                parsed_data["key_features"] = "\n".join(features)
    except Exception as e:
        print(f"LLM Analyzer: Error parsing patent summary response: {e}")
        # Fallback to raw response if parsing fails

    return parsed_data # Return dict with parsed fields or just raw_response


def analyze_infringement_per_evidence(patent_info, evidence_text, evidence_filename):
    """
    Uses LLM to analyze one piece of evidence against the patent.
    patent_info should be a dictionary from analyze_patent_text().
    """
    prompt = prompt_templates.INFRINGEMENT_ANALYSIS_PROMPT.format(
        patent_name=patent_info.get("patent_name", "N/A"),
        technical_field=patent_info.get("technical_field", "N/A"),
        core_claims=patent_info.get("core_claims", "N/A"),
        key_features=patent_info.get("key_features", "N/A"),
        target_product_description=evidence_text
    )

    print(f"LLM Analyzer: Requesting infringement analysis for evidence '{evidence_filename}' (text length: {len(evidence_text)}).")
    response_text = get_llm_response(prompt, max_tokens=1500, temperature=0.3) # Slightly higher temp for analysis

    # TODO: Parse the structured response (e.g., score, risk level, reasons)
    # For now, return the raw text.
    # A more robust solution would be to ask LLM for JSON output.
    parsed_analysis = {"raw_response": response_text, "evidence_filename": evidence_filename}
    # Basic parsing attempt:
    try:
        if "初步匹配度得分：" in response_text:
            score_line = [line for line in response_text.splitlines() if "初步匹配度得分：" in line][0]
            parsed_analysis["match_score_text"] = score_line.split("初步匹配度得分：")[1].strip().split("/")[0]
        if "风险等级：" in response_text or "结论与建议：" in response_text : # Example phrases
            # This is very naive, proper parsing or JSON from LLM is better
            if "高风险" in response_text: parsed_analysis["risk_level"] = "高风险"
            elif "中风险" in response_text: parsed_analysis["risk_level"] = "中风险"
            elif "低风险" in response_text: parsed_analysis["risk_level"] = "低风险"
    except Exception as e:
        print(f"LLM Analyzer: Error parsing infringement analysis response for {evidence_filename}: {e}")

    return parsed_analysis


def generate_final_report_summary(patent_info, all_evidence_analyses):
    """
    Uses LLM to generate a final summary report based on all analyses.
    all_evidence_analyses is a list of dicts from analyze_infringement_per_evidence().
    """
    individual_summaries_text = []
    for analysis in all_evidence_analyses:
        summary_item = f"### 线索：{analysis.get('evidence_filename', 'N/A')}\n"
        summary_item += f"匹配度得分：{analysis.get('match_score_text', 'N/A')}/100\n"
        summary_item += f"风险等级：{analysis.get('risk_level', 'N/A')}\n"
        # Include a snippet of the raw analysis for context if desired
        raw_snippet = analysis.get('raw_response', '分析不可用。')
        # Try to get a concise summary from the raw_response
        # This is where asking the INFRINGEMENT_ANALYSIS_PROMPT for a "简要分析" field would be useful
        # For now, just take first few lines as a placeholder for "简要分析"
        brief_analysis_placeholder = "\n".join(raw_snippet.splitlines()[1:4]) # Example: take 2nd to 4th lines
        summary_item += f"简要分析：{brief_analysis_placeholder}...\n---\n"
        individual_summaries_text.append(summary_item)

    prompt = prompt_templates.FINAL_REPORT_GENERATION_PROMPT.format(
        patent_name=patent_info.get("patent_name", "N/A"),
        technical_field=patent_info.get("technical_field", "N/A"),
        core_claims=patent_info.get("core_claims", "N/A"),
        key_features=patent_info.get("key_features", "N/A"),
        individual_analysis_summaries="\n".join(individual_summaries_text)
    )

    print(f"LLM Analyzer: Requesting final report generation.")
    final_report_text = get_llm_response(prompt, max_tokens=2000, temperature=0.2) # Max tokens higher for full report

    return final_report_text


if __name__ == '__main__':
    # Placeholder for local testing of LLM Analyzer functions
    print("LLM Analyzer module. Run `app.py` to use the system.")
    # Example (will use SIMULATE_LLM by default if no API key is set):
    # if settings.SIMULATE_LLM:
    # print("\n--- Testing Patent Text Analysis (Simulated) ---")
    # sample_patent_text = "这是一段示例专利文本，描述了一种创新的小装置及其制造方法。权利要求1：一种小装置，包含部件X和部件Y。权利要求2：一种制造上述小装置的方法。"
    # patent_analysis_result = analyze_patent_text(sample_patent_text)
    # print("Parsed Patent Info:", patent_analysis_result)

    # print("\n--- Testing Infringement Analysis (Simulated) ---")
    # sample_evidence_text = "某公司产品手册，描述的产品具有部件X和改进的部件Y'，功能相似。"
    # if patent_analysis_result and patent_analysis_result.get("raw_response"): # Use the result from previous step
    #     infringement_result = analyze_infringement_per_evidence(patent_analysis_result, sample_evidence_text, "sample_evidence.pdf")
    #     print("Infringement Analysis Result:", infringement_result)

    #     print("\n--- Testing Final Report Generation (Simulated) ---")
    #     final_report = generate_final_report_summary(patent_analysis_result, [infringement_result])
    #     print("Final Report (Simulated):\n", final_report)
    # else:
    #     print("Skipping further tests as patent_analysis_result was not sufficient.")
    pass
