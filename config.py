import os

# ==============================================================================
# LLM Configuration
# ==============================================================================

# OpenAI API Key
# It's recommended to load the API key from an environment variable for security.
# You can set it in your shell: export OPENAI_API_KEY='your_key_here'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'YOUR_DEFAULT_API_KEY')

# OpenAI API Base URL
# This is useful if you are using a proxy or a different API endpoint.
# For example, for local models or other compatible APIs.
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')

# Default LLM Model
# Specifies the default model to use for the analysis.
# Options include "gpt-4", "gpt-3.5-turbo", etc.
LLM_MODEL = "gpt-3.5-turbo"

# LLM Temperature
# Controls the randomness of the output. Higher values mean more random output.
# Value should be between 0.0 and 2.0.
LLM_TEMPERATURE = 0.5

# LLM Max Tokens
# The maximum number of tokens to generate in the response.
LLM_MAX_TOKENS = 2048

# ==============================================================================
# Application Configuration
# ==============================================================================

# Directory for storing uploads and generated reports
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')

# Path to the FlameGraph scripts directory
# Assumes the FlameGraph repo is cloned in the user's home directory.
# Update this path if FlameGraph is located elsewhere.
FLAMEGRAPH_DIR = os.path.expanduser('~/FlameGraph')
