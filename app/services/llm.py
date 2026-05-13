import os
from app.utils.logging import logger
import litellm

LLM_API_BASE = os.environ.get("LLM_API_BASE")


async def generate_response(model, messages):
    logger.info(f"Prompting LLM | model: {model} | api_base: {LLM_API_BASE}")

    # Using LiteLLM with a custom API base and the openai provider
    # We pass custom_llm_provider="openai" to ensure it treats the base as an OpenAI endpoint
    response = await litellm.acompletion(
        model=model,
        messages=messages,
        api_base=LLM_API_BASE,
        custom_llm_provider="openai" if LLM_API_BASE else None,
        api_key="sk-dummy",
        timeout=8.0,
    )

    return response
