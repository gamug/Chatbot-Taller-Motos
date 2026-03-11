import os

llm_config = {
    "api_key": os.environ["LLM_API_KEY"],
    "model": os.environ["LLM_MODEL"],
    "base_url": os.environ["LLM_URL"],
    "temperature": os.environ.get("LLM_TEMPERATURE", 0.7)
}