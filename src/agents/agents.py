import json, os, re, queue, threading
from strands import Agent, tool
from strands.agent.agent_result import AgentResult
from strands.models.openai import OpenAIModel

import config
from src import app_logger
from src.agents.handler import AnswerCallbackHandler
from src.agents.utils import get_available_brands_models, generate_html
from src.agents.agent_tools import (
    canonical_brand_models, query_knowledge_async, web_search
)

# Initialize as None - will be set by build_orchestrator_agent
_callback_handler = None

model = OpenAIModel(
    model_id=config.llm_config['model'],
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
        str: The best scored"brand-model" key from the dictionary coming from the canonical_brand_models tool.
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
        queries (list[str]): The rewritten query versions coming from query_versioning_agent in a list.
        canonical_brand_model (str): The best fit of possible canonical brand and model combinations coming from
            brand_model_agent.
    Returns:
        path (str): The path to the enriched chunks in json format.
    """
    app_logger.info("INSIDE query_knowledge_agent")
    agent = Agent(
        model=model,
        tools=[query_knowledge_async],
        system_prompt=config.prompts['KNOWLEDGE_QUERY_PROMPT'].format(query_copies=config.agent['query_copies']),
    )
    return agent(f"Query the knowledge database searching for question related chunks. The brand-model is '{canonical_brand_model}'. The queries are '{queries}'")

@tool
def answer_agent(chunks_path: str, user_question: str) -> str:
    """Agent to answer the user's question with a high-rich-technical markdown content.
    Args:
        chunks_path (str): The path to the enriched chunks OR full markdown text for greetings.
        user_question (str): The user's question or query that needs to be answered.
    Returns:
        str: Confirmation that the user's question was answered.
    """
    
    def create_and_run(non_related: bool=False) -> None:
        agent = Agent(
            model=model,
            tools=[],
            system_prompt=config.prompts['ANSWER_PROMPT'].format(language=config.agent['answer_language']),
            callback_handler=_callback_handler
        )
        if non_related:
            result["content"] = agent(
                "Seems like the user get confused and ask something weird."
                "Be kind and answer politely to asks a motorcycle related question."
                f"Just in case, the question was {user_question}."
                "If user want to be fun, be fun to but committing the provide motorcycle related question."
            )
        if enriched_chunks:
            result["content"] = agent(
                f"Answer the user's question '{user_question}' with a high-rich-technical markdown content. "
                f"Base your response on these enriched chunks: '{enriched_chunks}'. "
                f"Don't limit your answer to the user question: provide more related information contained in the chunks."
            )
        else:
            result["content"] = agent(
                "There's no chunks to answer the user's question. Answer the question with a clarification message. "
                "a. You should misunderstood the brand-model, ask user to be more specific providing canonical brand-model. "
                "b. You should misunderstood the user's question, ask user to be more specific and provide the query versions you tried."
            )

    # ... generate_html definition ...

    app_logger.info("Answering the user's question")

    user_confused = "NON MOTORCYCLE RELATED" in chunks_path
    if user_confused:
        create_and_run(non_related=True)
        return 'User confused. INTERACTION COMPLETE.'
    
    # --- greeting path: chunks_path is raw markdown content ---
    is_greeting = not os.path.exists(chunks_path)
    if is_greeting:
        app_logger.info("Greeting path — rendering markdown directly")
        content = chunks_path + get_available_brands_models()
        # stream to frontend
        if _callback_handler:
            kwargs = {'event': {'contentBlockDelta': {'delta': {'text': content}}}}
            _callback_handler(**kwargs)
        output_path = generate_html('capabilities.html', content)
        return f'Greeting answered and placed in {output_path}. INTERACTION COMPLETE.'

    # --- normal path: chunks_path is a file path ---
    with open(chunks_path, mode="r", encoding="utf-8") as f:
        enriched_chunks = json.loads(f.read())

    result = {}

    thread = threading.Thread(target=create_and_run)
    thread.start()
    thread.join()

    if not result.get("content"):
        return "User query was successfully answered but no chunks were found. INTERACTION COMPLETE."

    filename = re.sub(r'\W+', '_', user_question) + '.html'
    output_path = generate_html(filename, result["content"])
    return f'User query was successfully answered and placed in {output_path}. INTERACTION COMPLETE.'