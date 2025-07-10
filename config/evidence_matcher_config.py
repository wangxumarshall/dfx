# Configuration for the Infringement Evidence Matching Module

# LLM provider: "openai", "deepseek", "custom", etc.
LLM_PROVIDER = "openai" # or "deepseek"

# API Key - IMPORTANT: Best practice is to load this from environment variables or a secure vault
# For now, it can be set here for simplicity or referenced from main_config.py
# LLM_API_KEY = "YOUR_LLM_API_KEY_HERE" # Or reference main_config.OPENAI_API_KEY

# Model name for evidence matching tasks
EVIDENCE_MATCHING_MODEL_NAME = "gpt-3.5-turbo" # Example for OpenAI
# LLM_BASE_URL = "YOUR_LLM_API_BASE_URL_IF_NEEDED" # Or reference main_config.LLM_BASE_URL

# LLM request parameters
LLM_TEMPERATURE = 0.2
LLM_MAX_TOKENS = 1500
# LLM_TOP_P = 1.0

# Path to prompt templates or direct prompt strings
PATENT_SUMMARY_PROMPT_PATH = "prompts/evidence_matcher/patent_summary_prompt.txt"
INFRINGEMENT_ANALYSIS_PROMPT_PATH = "prompts/evidence_matcher/infringement_analysis_prompt.txt"

# Other module-specific settings
# For example, thresholds for considering a match, etc.
# MIN_MATCH_CONFIDENCE = 0.7
