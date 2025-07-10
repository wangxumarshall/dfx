# core/llm_analyzer.py
import time
# import openai # Or your chosen LLM library like `deepseek`
from config import settings
from prompts import prompt_templates

# --- LLM Client Initialization ---
# This is where you'd set up your API key and client.
# For OpenAI:
# if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-YOUR_"):
# openai.api_key = settings.OPENAI_API_KEY
# if hasattr(settings, 'LLM_BASE_URL') and settings.LLM_BASE_URL:
# openai.api_base = settings.LLM_BASE_URL # For self-hosted or proxies like LiteLLM, DeepSeek
# else:
# print("Warning: OPENAI_API_KEY not configured in settings.py or is a placeholder. LLM calls will fail.")
# pass # Or raise an error

# For DeepSeek (example, assuming a similar client library structure)
# if settings.OPENAI_API_KEY and "deepseek" in settings.LLM_MODEL_NAME.lower(): # Example check
#     try:
#         import deepseek
#         # deepseek.api_key = settings.OPENAI_API_KEY # Or specific DeepSeek key
#         # if hasattr(settings, 'LLM_BASE_URL') and settings.LLM_BASE_URL:
#         #     deepseek.api_base = settings.LLM_BASE_URL
#         print("DeepSeek client would be configured here.")
#     except ImportError:
#         print("Error: DeepSeek library not found. Please install it if you intend to use DeepSeek models.")


def get_llm_response(prompt, model_name=None, max_tokens=1500, temperature=0.2):
    """
    Generic function to get a response from the configured LLM.
    This will need to be adapted based on the specific LLM client library used (OpenAI, DeepSeek, etc.).
    """
    if settings.SIMULATE_LLM:
        print(f"\n--- SIMULATING LLM CALL ---")
        print(f"Model: {model_name or settings.LLM_MODEL_NAME}")
        print(f"Prompt (first 200 chars):\n{prompt[:200]}...\n")
        time.sleep(settings.SIMULATE_LLM_DELAY / 2) # Simulate network latency & processing

        # Simple simulation based on prompt type (very basic)
        if "PATENT_SUMMARY_PROMPT" in prompt_templates.__dict__.values(): # Check if it's a known prompt structure
             if prompt.startswith(prompt_templates.PATENT_SUMMARY_PROMPT.splitlines()[1][:50]): # Fragile check
                return """**专利名称**：模拟高效能源转换装置
**技术领域**：新能源
**核心权利要求**：
1. 一种包含A、B、C部件的能源转换装置，其特征在于...
2. 根据权利要求1所述的装置，其中C部件由特殊材料D制成...
**主要技术特点/创新点**：
- 采用了新型材料D，提升了转换效率20%。
- 独特的结构设计，减少了能量损失。"""

        if "INFRINGEMENT_ANALYSIS_PROMPT" in prompt_templates.__dict__.values():
            if prompt.startswith(prompt_templates.INFRINGEMENT_ANALYSIS_PROMPT.splitlines()[1][:50]):
                return """分析报告：
1.  **技术特征对比**：
    *   目标产品在特征A、B上与专利权利要求1一致。特征C略有不同，但功能相似。
2.  **侵权可能性评估**：
    *   **字面侵权可能性**：中。大部分特征匹配。
    *   **等同侵权可能性**：高。特征C的差异可能构成等同。
3.  **初步匹配度得分**：80/100。基于特征的广泛重叠。
4.  **抗辩理由初步考虑**: 暂无明显抗辩理由。
5.  **结论与建议**：高风险。建议进行详细法律评估。"""

        if "FINAL_REPORT_GENERATION_PROMPT" in prompt_templates.__dict__.values():
             if prompt.startswith(prompt_templates.FINAL_REPORT_GENERATION_PROMPT.splitlines()[1][:50]):
                return """生成的报告：
# 综合侵权分析报告 (模拟LLM)

## 1. 引言
本报告旨在分析“模拟高效能源转换装置”专利的潜在侵权风险。

## 2. 核心专利概述
**专利名称**：模拟高效能源转换装置
... (details from patent summary)

## 3. 侵权线索评估汇总
| 线索名称 | 匹配度 | 风险等级 | 关键理由 |
|----------|--------|----------|----------|
| product_X.pdf | 80/100 | 高风险   | 技术特征高度重叠 |
| competitor_Y.html | 60/100 | 中风险 | 部分特征相似，需进一步分析 |

...(further sections as per prompt)...
"""
        return "这是来自模拟LLM的通用响应。请检查您的提示和模拟逻辑。"


    # --- Actual LLM API Call (Example for OpenAI compatible APIs) ---
    # This part needs to be robust and handle API errors, rate limits, etc.
    try:
        # Placeholder for actual API call logic
        # For OpenAI / compatible:
        # messages = [{"role": "user", "content": prompt}]
        # response = openai.ChatCompletion.create(
        #     model=model_name or settings.LLM_MODEL_NAME,
        #     messages=messages,
        #     max_tokens=max_tokens,
        #     temperature=temperature,
        #     # top_p=1, # Adjust other parameters as needed
        #     # frequency_penalty=0,
        #     # presence_penalty=0
        # )
        # return response.choices[0].message.content.strip()

        # Replace with your specific LLM client call:
        print(f"Attempting REAL LLM call to model: {model_name or settings.LLM_MODEL_NAME}")
        print("ERROR: Real LLM call logic is not fully implemented in `core/llm_analyzer.py`.")
        print("Please implement the API call for your chosen LLM provider.")
        raise NotImplementedError("LLM API call logic needs to be implemented for the chosen provider.")

    except Exception as e: # Catch specific API errors if possible
        print(f"LLM API call failed: {e}")
        # Fallback, retry, or raise
        return f"[LLM_ERROR: {e}]"


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
