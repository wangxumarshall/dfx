# Configuration for the Infringement Evidence Reliability Assessment Module

# Enable or disable this module entirely
ASSESSOR_ENABLED = False # Default to False as per requirements

# Assessment method: "llm", "rules_based", "hybrid"
ASSESSMENT_METHOD = "llm"

# --- Settings for "llm" based assessment ---
# LLM provider details (can be same or different from evidence_matcher)
# LLM_PROVIDER = "openai"
# LLM_API_KEY = "YOUR_LLM_API_KEY_HERE" # Or reference main_config.OPENAI_API_KEY
ASSESSMENT_MODEL_NAME = "gpt-3.5-turbo"
# ASSESSMENT_LLM_BASE_URL = "YOUR_LLM_API_BASE_URL_IF_NEEDED"

# LLM request parameters for assessment
ASSESSMENT_LLM_TEMPERATURE = 0.1
ASSESSMENT_LLM_MAX_TOKENS = 500

# Path to prompt templates for reliability assessment
RELIABILITY_ASSESSMENT_PROMPT_PATH = "prompts/reliability_assessor/assessment_prompt.txt"

# --- Settings for "rules_based" assessment ---
# Path to rules definition file (e.g., YAML, JSON)
# RULES_FILE_PATH = "configs/reliability_rules.yaml" # Example
# Default reliability score if no rules match or for baseline
# DEFAULT_RELIABILITY_SCORE = 50

# --- Settings for "hybrid" assessment ---
# Weights for combining LLM and rules-based scores if applicable
# LLM_SCORE_WEIGHT = 0.7
# RULES_SCORE_WEIGHT = 0.3
