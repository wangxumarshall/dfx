import os

class Settings:
    # --- LLM Provider Configuration ---
    # Choose your provider: "openai", "deepseek", "ollama", "none"
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

    # --- API Keys and Base URLs ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-YOUR_OPENAI_API_KEY")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-YOUR_DEEPSEEK_API_KEY")
    # For self-hosted models or proxies like LiteLLM
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", None)

    # --- Model Configuration ---
    # Model name, e.g., "gpt-4-turbo", "deepseek-coder", "llama3"
    LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-3.5-turbo")
    # Max tokens for the completion
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 1500))
     # Temperature for sampling
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.2))

    # --- Simulation Mode ---
    # If True, the LLM call will be simulated.
    SIMULATE_LLM = os.getenv("SIMULATE_LLM", "False").lower() in ('true', '1', 't')
    # Delay in seconds for simulated LLM responses
    SIMULATE_LLM_DELAY = int(os.getenv("SIMULATE_LLM_DELAY", 2))

# Instantiate settings
settings = Settings()

# --- Validation and Warnings ---
if settings.LLM_PROVIDER not in ["openai", "deepseek", "ollama", "none"]:
    print(f"Warning: Unknown LLM_PROVIDER '{settings.LLM_PROVIDER}'. Defaulting to 'none'.")
    settings.LLM_PROVIDER = "none"

if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY.startswith("sk-YOUR_"):
    print("Warning: OpenAI API key is a placeholder. Please set the OPENAI_API_KEY environment variable.")

if settings.LLM_PROVIDER == "deepseek" and settings.DEEPSEEK_API_KEY.startswith("sk-YOUR_"):
    print("Warning: DeepSeek API key is a placeholder. Please set the DEEPSEEK_API_KEY environment variable.")

if settings.LLM_BASE_URL:
    print(f"Info: Using custom LLM base URL: {settings.LLM_BASE_URL}")
