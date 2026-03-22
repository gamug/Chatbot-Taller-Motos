from strands import Agent, tool
from strands.agent.agent_result import AgentResult
from strands.models.openai import OpenAIModel

import config
from src import app_logger
from src.agents.agent_tools import (
    canonical_brand_models, folder_integrity, query_knowledge, web_search,
    file_write
)


model = OpenAIModel(
    model_id=config.llm_config['model'],  # or "deepseek-reasoner" for R1
    client_args={
        "api_key": config.llm_config['api_key'],
        "base_url": config.llm_config['base_url']
    }
)

@tool
def brand_model_agent(query: str) -> AgentResult:
    """Agent to extract the brand and model from the user's question.
    Args:
        query (str): The user's question or query that needs to be answered based on the motorcycle manuals.
    Returns:
        str: The extracted brand and model in format lower case like "brand-model", e.g. "bajaj-ns200".
    """
    agent = Agent(
        model=model,
        tools=[canonical_brand_models, web_search],
        system_prompt=config.prompts['BRAND_MODEL_PROMPT'].format(score=config.agent['canonical_brand_score'])
    )
    return agent(f"Extract the brand and model from the user's question: '{query}'")

@tool
def query_versioning_agent(query: str) -> AgentResult:
    """Agent to make query versions in clear-technical way to perform vectorial search.
    Args:
        query (str): The user's question or query that needs to be answered.
    Returns:
        str: The user query versions in a list wrote in english.
    """
    app_logger.info("Trying to make query versions in clear-technical way to prepare vectorial search")
    agent = Agent(
        model=model,
        system_prompt=config.prompts['REWRITE_PROMPT'].format(query_copies=config.agent['query_copies'])
    )
    versions =  agent(f"Make versions of the user's question excluding the motorcycle brand-model: '{query}'")
    app_logger.info(f"Query versions: {versions}")
    return versions

@tool
def query_knowledge_agent(queries: list[str], canonical_brand_model: str) -> AgentResult:
    """Agent to querying the knowledge and structure solid-technical knowledge to be consumed by the orchestrator.
    Args:
        queries (list[str]): The rewritten query versions in a list.
        canonical_brand_model (str): The best fit of possible canonical brand and model combinations.
    Returns:
        chunk_list (list[str]): The relevant context retrieved from the knowledge database enriched by the llm
        that can be used to answer the user's question.
    """
    app_logger.info("Querying knowledge database searching for question related chunks")
    agent = Agent(
        model=model,
        tools=[query_knowledge],
        system_prompt=config.prompts['KNOWLEDGE_QUERY_PROMPT'],
    )
    return agent(f"Query the knowledge database searching for question related chunks. The brand-model is '{canonical_brand_model}'. The query is '{queries}'")