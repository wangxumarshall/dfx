# core/report_generator.py
import os
import time
from config import settings

def generate_markdown_report(patent_analysis_data, evidence_analysis_results, report_filename_base, session_id):
    """
    Generates a Markdown formatted report from the analysis data.

    Args:
        patent_analysis_data (dict): Data from llm_analyzer.analyze_patent_text()
                                     e.g., {"patent_name": "...", "technical_field": "...", "core_claims": "...",
                                            "key_features": "...", "raw_response": "..."}
        evidence_analysis_results (list): List of dicts from llm_analyzer.analyze_infringement_per_evidence()
                                          e.g., [{"raw_response": "...", "evidence_filename": "...",
                                                  "match_score_text": "75", "risk_level": "高风险"}, ...]
        report_filename_base (str): The base name for the report file (e.g., "report_timestamp_uuid.md")
        session_id (str): The unique session ID for this analysis.

    Returns:
        str: Path to the generated markdown report.
    """

    report_path = os.path.join(settings.REPORTS_FOLDER, report_filename_base)

    # Extract data safely with fallbacks
    patent_name = patent_analysis_data.get("patent_name", "未能提取专利名称")
    tech_field = patent_analysis_data.get("technical_field", "未能提取技术领域")
    core_claims = patent_analysis_data.get("core_claims", "未能提取核心权利要求")
    key_features = patent_analysis_data.get("key_features", "未能提取主要技术特点")

    # If the LLM provided a full structured summary for the patent, we can use that directly
    # For now, we construct it from parsed fields.
    # patent_summary_llm_raw = patent_analysis_data.get("raw_response", "LLM原始专利分析响应不可用。")


    # --- Start Markdown Content ---
    md_content = f"# 专利侵权风险分析报告\n\n"
    md_content += f"**报告生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    md_content += f"**分析任务ID**: {session_id}\n\n"
    md_content += "---\n\n"

    md_content += f"## 1. 核心专利信息\n\n"
    md_content += f"**专利名称**: {patent_name}\n\n"
    md_content += f"**技术领域**: {tech_field}\n\n"
    md_content += f"**核心权利要求**:\n```\n{core_claims}\n```\n\n"
    md_content += f"**主要技术特点与创新点**:\n```\n{key_features}\n```\n\n"
    # md_content += f"### 1.5 LLM对专利的原始分析摘要\n\n" # Optional: include raw LLM output for patent
    # md_content += f"```\n{patent_summary_llm_raw}\n```\n\n"
    md_content += "---\n\n"

    md_content += f"## 2. 潜在侵权线索分析\n\n"
    if not evidence_analysis_results:
        md_content += "未提供侵权线索文件，或未能成功分析任何线索。\n\n"
    else:
        md_content += f"共分析了 {len(evidence_analysis_results)} 个潜在侵权线索文件。\n\n"

        # Summary Table
        md_content += "### 2.1 线索汇总表\n\n"
        md_content += "| 线索文件名 | 匹配度得分 (模拟) | 风险等级 (模拟) | 主要发现 (简述) |\n"
        md_content += "|------------|-------------------|-----------------|-----------------|\n"
        for i, result in enumerate(evidence_analysis_results):
            fname = result.get('evidence_filename', f'线索_{i+1}')
            score = result.get('match_score_text', 'N/A')
            risk = result.get('risk_level', 'N/A')

            # Basic summary from raw_response (placeholder - LLM should ideally provide this)
            raw_analysis = result.get('raw_response', '')
            brief_summary = " ".join(raw_analysis.splitlines()[1:3]).replace("*","").strip() # very naive summary
            if not brief_summary : brief_summary = "见详细分析"

            md_content += f"| {os.path.basename(fname)} | {score} | {risk} | {brief_summary[:100]}{'...' if len(brief_summary)>100 else ''} |\n"
        md_content += "\n"

        # Detailed Analysis for each evidence
        md_content += "### 2.2 各线索详细分析 (LLM提供)\n\n"
        for i, result in enumerate(evidence_analysis_results):
            fname = result.get('evidence_filename', f'线索_{i+1}')
            raw_analysis_text = result.get('raw_response', f"未能获取对 {fname} 的详细分析文本。")

            md_content += f"#### 2.2.{i+1} 线索: {os.path.basename(fname)}\n\n"
            # The raw_analysis_text from LLM is expected to be markdown-friendly or plain text
            # that will be rendered within a block.
            md_content += f"```markdown\n{raw_analysis_text}\n```\n\n" # Wrapping in markdown block for clarity
            md_content += "---\n"

    md_content += "\n## 3. 综合结论与建议 (LLM提供)\n\n"
    # This part would ideally be a separate call to the LLM (generate_final_report_summary in llm_analyzer)
    # For now, if that function was called and its result passed here, we'd use it.
    # Assuming `patent_analysis_data` might contain a "final_summary_llm_raw" key if that step was done.
    final_summary_text = patent_analysis_data.get("final_summary_llm_raw",
                                                 "最终的综合结论与建议部分需要由LLM在分析完所有线索后单独生成。此部分为占位符。\n" \
                                                 "（模拟场景下，此内容可能由 `llm_analyzer.generate_final_report_summary` 函数填充）。")
    md_content += f"{final_summary_text}\n\n"

    md_content += "---\n\n"
    md_content += f"*免责声明: 本报告由AI系统生成，仅供参考，不构成任何法律意见。请结合专业人士的判断进行决策。*\n"

    # --- Write to File ---
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Markdown report generated successfully: {report_path}")
        return report_path
    except IOError as e:
        print(f"Error writing report file {report_path}: {e}")
        return None

if __name__ == '__main__':
    # Placeholder for local testing of report generator
    print("Report generator module. Run `app.py` to use the system.")

    # Dummy data for testing generate_markdown_report
    # if settings.SIMULATE_LLM: # Ensure this test runs only if simulation is on, or adjust paths
    #     print("\n--- Testing Markdown Report Generation (Simulated Data) ---")

    #     dummy_patent_data = {
    #         "patent_name": "革命性即时传送装置",
    #         "technical_field": "量子物理与空间折叠技术",
    #         "core_claims": "1. 一种能够实现物质瞬间转移的装置，包含A、B、C三个核心模块。\n2. 根据权利要求1，其中模块A负责...",
    #         "key_features": "- 采用反重力稳定立场。\n- 能源消耗降低90%。",
    #         "raw_response": "这是LLM对专利的原始分析...",
    #         # "final_summary_llm_raw": "# 最终总结报告\n经过分析，我们认为..." # This would come from another LLM call
    #     }

    #     dummy_evidence_results = [
    #         {
    #             "evidence_filename": "competitor_alpha_product_specs.pdf",
    #             "match_score_text": "85",
    #             "risk_level": "高风险",
    #             "raw_response": """分析报告 for competitor_alpha_product_specs.pdf:
    #             1.  **技术特征对比**：与专利特征A, B高度相似。特征C采用替代方案C'。
    #             2.  **侵权可能性评估**：字面侵权（中），等同侵权（高）。
    #             3.  **初步匹配度得分**：85/100。
    #             4.  **结论与建议**：高风险，建议深入调查。"""
    #         },
    #         {
    #             "evidence_filename": "research_paper_on_similar_tech.md",
    #             "match_score_text": "40",
    #             "risk_level": "低风险",
    #             "raw_response": """分析报告 for research_paper_on_similar_tech.md:
    #             1.  **技术特征对比**：仅在概念层面提及类似技术，无具体实现细节匹配。
    #             2.  **侵权可能性评估**：低。
    #             3.  **初步匹配度得分**：40/100。
    #             4.  **结论与建议**：低风险，关注其后续发展。"""
    #         }
    #     ]

    #     # Ensure reports directory exists for the test
    #     if not os.path.exists(settings.REPORTS_FOLDER):
    #         os.makedirs(settings.REPORTS_FOLDER)

    #     report_file = generate_markdown_report(
    #         dummy_patent_data,
    #         dummy_evidence_results,
    #         f"test_report_{time.strftime('%Y%m%d%H%M%S')}.md",
    #         "test-session-123"
    #     )

    #     if report_file:
    #         print(f"Test report generated at: {report_file}")
    #         # Optional: print content for quick check
    #         # with open(report_file, 'r', encoding='utf-8') as f_rep:
    #         #     print("\n--- Report Content ---")
    #         #     print(f_rep.read(1000) + "...")
    #     else:
    #         print("Test report generation failed.")
    pass
