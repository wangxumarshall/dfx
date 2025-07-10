# Configuration for the Infringement Report Generation Module

# Default report format (though Markdown is primary, this could influence sub-components)
DEFAULT_REPORT_FORMAT = "markdown"

# Path to Markdown template files or fragments for report sections
# REPORT_TEMPLATE_DIR = "templates/report_parts/" # Example
HEADER_TEMPLATE = "templates/report_templates/default_header.md"
PATENT_INFO_TEMPLATE = "templates/report_templates/default_patent_info.md"
EVIDENCE_SUMMARY_TEMPLATE = "templates/report_templates/default_evidence_summary.md"
EVIDENCE_DETAIL_TEMPLATE = "templates/report_templates/default_evidence_detail.md"
RELIABILITY_INFO_TEMPLATE = "templates/report_templates/default_reliability_info.md" # If assessor is enabled
CONCLUSION_TEMPLATE = "templates/report_templates/default_conclusion.md"
FOOTER_TEMPLATE = "templates/report_templates/default_footer.md"

# Report output settings
DEFAULT_REPORTS_FOLDER = "reports" # This might be better in main_config.py or app.py

# Options for PDF conversion via WeasyPrint (if applicable)
# PDF_STYLESHEET_PATH = "static/css/report_pdf_style.css" # Example

# Whether to include raw LLM responses in the report (for debugging or transparency)
INCLUDE_RAW_LLM_RESPONSES = False

# Disclaimer text for the report
REPORT_DISCLAIMER = "免责声明: 本报告由AI系统生成，分析结果仅供参考，不构成任何法律意见或建议。请结合专业人士的判断进行决策。"
