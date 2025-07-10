# modules/report_generator/generator.py
import os
import datetime
import json

try:
    from config import main_config
    from config import report_generator_config
except ImportError:
    print("WARN: ReportGenerator: Error importing configs. Using fallback defaults.")
    class main_config: #type: ignore
        SIMULATE_LLM = True # Not directly used but for consistency
    class report_generator_config: #type: ignore
        HEADER_TEMPLATE = "templates/report_templates/default_header.md"
        PATENT_INFO_TEMPLATE = "templates/report_templates/default_patent_info.md"
        EVIDENCE_SUMMARY_TABLE_TEMPLATE = "templates/report_templates/default_evidence_summary_table.md"
        EVIDENCE_DETAIL_TEMPLATE = "templates/report_templates/default_evidence_detail.md"
        RELIABILITY_INFO_TEMPLATE = "templates/report_templates/default_reliability_info.md"
        CONCLUSION_TEMPLATE = "templates/report_templates/default_conclusion.md"
        FOOTER_TEMPLATE = "templates/report_templates/default_footer.md"
        REPORT_DISCLAIMER = "Fallback Disclaimer: AI analysis, for reference only."
        INCLUDE_RAW_LLM_RESPONSES = False


class ReportGenerator:
    def __init__(self):
        self.template_paths = {
            "header": report_generator_config.HEADER_TEMPLATE,
            "patent_info": report_generator_config.PATENT_INFO_TEMPLATE,
            "summary_table": report_generator_config.EVIDENCE_SUMMARY_TEMPLATE, # Corrected: Use EVIDENCE_SUMMARY_TEMPLATE
            "evidence_detail": report_generator_config.EVIDENCE_DETAIL_TEMPLATE,
            "reliability_info": report_generator_config.RELIABILITY_INFO_TEMPLATE,
            "conclusion": report_generator_config.CONCLUSION_TEMPLATE,
            "footer": report_generator_config.FOOTER_TEMPLATE,
        }
        self.templates = self._load_templates()
        self.disclaimer = report_generator_config.REPORT_DISCLAIMER
        self.include_raw_llm = report_generator_config.INCLUDE_RAW_LLM_RESPONSES

        print("INFO: ReportGenerator initialized.")

    def _load_templates(self):
        loaded_templates = {}
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Project root

        for key, path in self.template_paths.items():
            full_path = os.path.join(base_path, path)
            if not os.path.exists(full_path): # Fallback to CWD if not found from project root
                full_path = path

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    loaded_templates[key] = f.read()
            except FileNotFoundError:
                print(f"ERROR: ReportGenerator: Template file not found: {full_path}. Using empty string for '{key}'.")
                loaded_templates[key] = f"[Template Error: {path} not found]"
            except Exception as e:
                print(f"ERROR: ReportGenerator: Error loading template {full_path}: {e}. Using empty string for '{key}'.")
                loaded_templates[key] = f"[Template Error: {path} loading failed - {e}]"
        return loaded_templates

    def _format_list_to_md(self, data_list, indent=0):
        if not isinstance(data_list, list):
            return str(data_list) # Or handle error
        prefix = "  " * indent + "- "
        return "\n".join([f"{prefix}{item}" for item in data_list]) if data_list else "N/A"

    def _format_claim_comparison(self, claim_comparisons):
        if not isinstance(claim_comparisons, list):
            return "N/A"

        formatted_text = ""
        for i, comp in enumerate(claim_comparisons):
            formatted_text += f"  **Claim {comp.get('claim_number', i+1)}** (Snippet: `{comp.get('claim_text_snippet', 'N/A')}`):\n"
            formatted_text += f"  Overall Match Status: {comp.get('overall_claim_match_status', 'N/A')}\n"
            if comp.get('elements_mapping'):
                for elem_map in comp['elements_mapping']:
                    formatted_text += f"    - Patent Element: `{elem_map.get('patent_element', 'N/A')}`\n"
                    formatted_text += f"      Mapping Status: {elem_map.get('evidence_mapping_status', 'N/A')}\n"
                    formatted_text += f"      Evidence Support: {elem_map.get('evidence_support_snippet', 'N/A')}\n"
            formatted_text += "\n"
        return formatted_text.strip() if formatted_text else "No claim comparison data provided."


    def generate_report(self, patent_data, all_evidence_analyses, report_metadata=None):
        """
        Generates a comprehensive Markdown report.
        Args:
            patent_data (dict): Structured patent information. Expected keys from patent_summary_prompt.
            all_evidence_analyses (list): List of dicts, results from EvidenceMatcher & ReliabilityAssessor.
            report_metadata (dict, optional): Contains 'task_id', 'generation_time'.
        Returns:
            str: The complete Markdown report.
        """
        if report_metadata is None:
            report_metadata = {}

        report_parts = []

        # 1. Header
        header_content = self.templates.get("header", "").format(
            generation_time=report_metadata.get("generation_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            task_id=report_metadata.get("task_id", "N/A")
        )
        report_parts.append(header_content)

        # 2. Patent Info
        patent_info_content = self.templates.get("patent_info", "").format(
            patent_title=patent_data.get("patent_title", "N/A"),
            publication_number=patent_data.get("publication_number", "N/A"),
            assignee=patent_data.get("assignee", "N/A"),
            priority_date=patent_data.get("priority_date", "N/A"),
            technical_field=patent_data.get("technical_field", "N/A"),
            problem_solved=patent_data.get("problem_solved", "N/A"),
            solution_summary=patent_data.get("solution_summary", "N/A"),
            key_claims_verbatim=self._format_list_to_md(patent_data.get("key_claims_verbatim", ["N/A"])), # Corrected: Use _format_list_to_md
            novelty_points=self._format_list_to_md(patent_data.get("novelty_points", ["N/A"])),
            main_components_or_steps=self._format_list_to_md(patent_data.get("main_components_or_steps", ["N/A"]))
        )
        report_parts.append(patent_info_content)

        # 3. Evidence Summary Table
        summary_table_rows = []
        for i, analysis in enumerate(all_evidence_analyses):
            reliability_info = analysis.get("reliability_assessment", {})
            reliability_score = "N/A (Not Assessed)"
            if reliability_info.get("status") == "disabled":
                 reliability_score = "N/A (Disabled)"
            elif not reliability_info.get("error"):
                 reliability_score = reliability_info.get("reliability_score_of_previous_analysis", "N/A")


            row = f"| {i+1} | {analysis.get('clue_identifier', 'N/A')} | {analysis.get('overall_infringement_risk_score', 'N/A')} | {analysis.get('literal_infringement_likelihood', 'N/A')} | {analysis.get('doctrine_of_equivalents_likelihood', 'N/A')} | {reliability_score} |"
            summary_table_rows.append(row)

        summary_table_content = self.templates.get("summary_table", "").format(
            total_clues_analyzed=len(all_evidence_analyses),
            summary_table_rows="\n".join(summary_table_rows)
        )
        report_parts.append(summary_table_content)
        report_parts.append("## 2.1 各线索详细分析\n") # Add sub-header for details

        # 4. Evidence Details
        for i, analysis in enumerate(all_evidence_analyses):
            detail_content = self.templates.get("evidence_detail", "").format(
                clue_sequence_number=f"2.1.{i+1}", # Using 2.1.x for sequence
                clue_identifier=analysis.get('clue_identifier', 'N/A'),
                overall_infringement_risk_score=analysis.get('overall_infringement_risk_score', 'N/A'),
                literal_infringement_likelihood=analysis.get('literal_infringement_likelihood', 'N/A'),
                doctrine_of_equivalents_likelihood=analysis.get('doctrine_of_equivalents_likelihood', 'N/A'),
                key_evidence_features=self._format_list_to_md(analysis.get('key_evidence_features', [])),
                claim_comparison_details=self._format_claim_comparison(analysis.get('claim_comparison', [])),
                reasoning_summary=analysis.get('reasoning_summary', 'N/A'),
                strengths_of_infringement_case=self._format_list_to_md(analysis.get('strengths_of_infringement_case', [])),
                weaknesses_of_infringement_case_or_potential_defenses=self._format_list_to_md(analysis.get('weaknesses_of_infringement_case_or_potential_defenses', []))
            )
            report_parts.append(detail_content)

            # 4.1 Reliability Info (if available and no error)
            reliability_data = analysis.get("reliability_assessment", {})
            if reliability_data and reliability_data.get("status") != "disabled" and not reliability_data.get("error"):
                reliability_content = self.templates.get("reliability_info", "").format(
                    reliability_score_of_previous_analysis=reliability_data.get('reliability_score_of_previous_analysis', 'N/A'),
                    assessment_summary=reliability_data.get('assessment_summary', 'N/A'),
                    points_of_concern_in_previous_analysis=self._format_list_to_md(reliability_data.get('points_of_concern_in_previous_analysis', [])),
                    points_of_strength_in_previous_analysis=self._format_list_to_md(reliability_data.get('points_of_strength_in_previous_analysis', []))
                )
                report_parts.append(reliability_content)
            elif reliability_data and reliability_data.get("status") == "disabled":
                 report_parts.append(f"**可靠性评估**: {reliability_data.get('message', '评估已禁用')}\n---")
            elif reliability_data and reliability_data.get("error"):
                 report_parts.append(f"**可靠性评估错误**: {reliability_data.get('error')} - {reliability_data.get('details', '')}\n---")


            if self.include_raw_llm and isinstance(analysis, dict): # Optional: include raw LLM output for evidence match
                raw_match_output = {k: v for k, v in analysis.items() if k != 'reliability_assessment'}
                report_parts.append(f"\n<details><summary>原始匹配分析JSON (点击展开)</summary>\n\n```json\n{json.dumps(raw_match_output, indent=2, ensure_ascii=False)}\n```\n</details>\n---")


        # 5. Conclusion
        # The actual text for conclusion ideally comes from an LLM call or a more sophisticated logic.
        # For now, it's a placeholder in the template or can be passed in patent_data or a separate arg.
        overall_conclusion = patent_data.get("overall_conclusion_and_recommendation_text",
                                             "请根据以上详细分析，综合评估整体风险并制定相应策略。AI分析仅供参考。")
        conclusion_content = self.templates.get("conclusion", "").format(
            overall_conclusion_and_recommendation_text=overall_conclusion
        )
        report_parts.append(conclusion_content)

        # 6. Footer
        footer_content = self.templates.get("footer", "").format(report_disclaimer=self.disclaimer)
        report_parts.append(footer_content)

        return "\n\n".join(report_parts)

if __name__ == '__main__':
    print("--- ReportGenerator Test ---")
    generator = ReportGenerator()

    # Sample data (mimicking outputs from previous modules)
    sample_patent_data = {
        "patent_title": "革命性即时传送装置", "publication_number": "WO 2025/12345",
        "assignee": "未来科技公司", "priority_date": "2024-01-15",
        "technical_field": "量子物理与空间折叠技术",
        "problem_solved": "解决传统运输方式的低效与高耗时问题。",
        "solution_summary": "本发明提出一种基于量子纠缠和微型虫洞生成技术的即时物质传送装置与方法。",
        "key_claims_verbatim": [
            "1. 一种物质传送装置，其特征在于，包括：量子纠缠模块；微型虫洞发生器；以及目标坐标锁定系统。",
            "2. 根据权利要求1所述的装置，其中所述量子纠缠模块用于建立传送物品与其目标位置副本之间的纠缠对。"
        ],
        "novelty_points": ["首次实现宏观物体稳定量子纠缠态的建立与维持。", "采用动态调整的微型虫洞技术，降低能量消耗。"],
        "main_components_or_steps": ["量子纠缠模块", "微型虫洞发生器", "目标坐标锁定系统", "能量稳定单元"],
        "overall_conclusion_and_recommendation_text": "综合分析，该专利具有较强的技术壁垒。针对当前分析的线索，建议对高风险线索进行进一步的技术和法律评估。低风险线索可暂时搁置，但保持关注。"
    }

    sample_evidence_analyses = [
        { # Clue 1 - High risk, reliability assessed
            "clue_identifier": "CompetitorX_TeleporterAlpha.pdf",
            "overall_infringement_risk_score": 85,
            "literal_infringement_likelihood": "High",
            "doctrine_of_equivalents_likelihood": "Medium",
            "key_evidence_features": ["采用量子链接", "空间折叠通道", "GPS定位"],
            "claim_comparison": [{
                "claim_number": "Claim 1", "claim_text_snippet": "一种物质传送装置...",
                "elements_mapping": [
                    {"patent_element": "量子纠缠模块", "evidence_mapping_status": "Found Equivalently", "evidence_support_snippet": "产品手册提及“量子链接”"},
                    {"patent_element": "微型虫洞发生器", "evidence_mapping_status": "Found", "evidence_support_snippet": "技术白皮书描述了“空间折叠通道”原理"},
                    {"patent_element": "目标坐标锁定系统", "evidence_mapping_status": "Found", "evidence_support_snippet": "使用高精度GPS进行目标锁定"}
                ], "overall_claim_match_status": "All Elements Found"
            }],
            "reasoning_summary": "产品特征与专利权利要求1高度吻合，构成高侵权风险。",
            "strengths_of_infringement_case": ["所有核心组件均在竞品中找到对应或等同物。"],
            "weaknesses_of_infringement_case_or_potential_defenses": ["“量子链接”与“量子纠缠”的具体技术实现可能存在差异，需进一步分析等同性。"],
            "reliability_assessment": {
                "reliability_score_of_previous_analysis": 90,
                "assessment_summary": "先前分析的结论可信度高，理由充分，证据引用明确。",
                "points_of_concern_in_previous_analysis": [],
                "points_of_strength_in_previous_analysis": ["对每个权利要求元素的映射清晰。", "风险评分与理由一致。"]
            }
        },
        { # Clue 2 - Low risk, reliability assessor disabled for this one
            "clue_identifier": "ResearchPaper_QuantumTransportIdeas.md",
            "overall_infringement_risk_score": 30,
            "literal_infringement_likelihood": "Low",
            "doctrine_of_equivalents_likelihood": "None",
            "key_evidence_features": ["理论探讨量子传输", "未提及虫洞"],
            "claim_comparison": [{
                "claim_number": "Claim 1", "claim_text_snippet": "一种物质传送装置...",
                "elements_mapping": [
                    {"patent_element": "量子纠缠模块", "evidence_mapping_status": "Partially Found", "evidence_support_snippet": "论文讨论了量子态传输理论"},
                    {"patent_element": "微型虫洞发生器", "evidence_mapping_status": "Not Found", "evidence_support_snippet": "未提及类似技术"}
                ], "overall_claim_match_status": "Some Elements Missing"
            }],
            "reasoning_summary": "研究论文仅为理论探讨，缺少关键技术组件的实现描述，侵权风险低。",
            "strengths_of_infringement_case": [],
            "weaknesses_of_infringement_case_or_potential_defenses": ["关键组件“微型虫洞发生器”缺失。", "仅为理论层面，非实际产品。"],
            "reliability_assessment": {"status": "disabled", "message": "Reliability assessor was not enabled for this item."}
        }
    ]

    report_meta = {"task_id": "TEST-TASK-001", "generation_time": "2024-07-29 10:00:00"}

    markdown_report = generator.generate_report(sample_patent_data, sample_evidence_analyses, report_meta)

    print("\n--- Generated Markdown Report ---")
    print(markdown_report)

    # Save report to file for inspection
    output_report_path = "test_generated_report.md"
    with open(output_report_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)
    print(f"\nReport saved to: {os.path.abspath(output_report_path)}")

    print("\n--- ReportGenerator Test Complete ---")
