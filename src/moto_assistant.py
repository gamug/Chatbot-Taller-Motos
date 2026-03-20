import json
from langgraph.graph import StateGraph, END

import config
from src.commons import (
    AWSClient, get_brands, get_llm, extract_moto_models
)
from src import app_logger
from src.types.state import AssistantState


brands = get_brands()
llm = get_llm()
aws_client = AWSClient()

def domain_guard(state: AssistantState):
    app_logger.info("="*20)
    app_logger.info("INSIDE intent NODE")
    app_logger.info("New question sent")
    prompt = f"""
    Determine if the query is motorcycles related, non related or user saying hello.
    Query: {state['query']}
    TRUE: If the query is motorcycle related
    FALSE: If the query is non motorcycle related
    HELLO: If the query is user saying hello
    Answer without introductory text or additional comments.
    """
    result = llm.invoke(prompt)
    app_logger.info(f"query: {state['query']}")
    app_logger.info(f"Intent: {result.content.upper()}")
    return {
        "is_motorcycle_related": result.content.upper()
    }

def ask_clarification(state):
    app_logger.info("INSIDE ask_clarification NODE")
    app_logger.warning("Agent was unable to get brand-model, the system will respond asking for user clarification")
    models = state["detected_models"]
    options = [m['brand'] for m in models]
    app_logger.info(f"Possible motorcycle options: {options}")
    if len(options):
        options = "  \n- " + "  \n- ".join(options)
        return {
            "answer": f"Encontré las siguientes motocicletas que pueden coincidir con tu búsqueda:\n {options}"
        }
    return {
        "answer": "No encontré la motocicleta que buscas ¿Puedes ser mas especifico?"
    }

def model_extraction(state: AssistantState):
    """
    Extracts the motorcycle models from the user query.
    Args:
        state: AssistantState
    Returns:
        dict: A dictionary containing the detected motorcycle models.
    """
    app_logger.info("INSIDE model_extraction NODE")
    models = extract_moto_models(state["query"], llm, brands)
    app_logger.info(f"Detected motorcycle models: {models}")
    return {"detected_models": models}

def model_resolution(state: AssistantState):
    app_logger.info("INSIDE model_resolution NODE")
    models = state["detected_models"]
    if not models:
        return {"model_confident": False}
    best = sorted(models, key=lambda x: x["score"], reverse=True)[0]
    if best["score"] < 0.75:
        return {"model_confident": False}
    return {
        "model_confident": True,
        "selected_model": best
    }

def query_rewriter(state: AssistantState):
    app_logger.info("INSIDE query_rewriter NODE")
    model = state["selected_model"]
    prompt = f"""
    Rewrite the query to improve search in a motorcycle manual.
    Motorcycle: {model['brand']}
    User query: {state['query']}
    Provide the rewritten query without introductory text or additional comments.
    Provide a single version in english, the best for the query.
    """
    brand, mod = model["brand"].split('-')
    rewritten_query = llm.invoke(prompt).content.lower()
    rewritten_query = rewritten_query.replace(brand, '').replace(mod, '')
    app_logger.info(f"Rewritten query: {rewritten_query}")
    return {
        "rewritten_query": rewritten_query
    }

def vector_retrieval(state: AssistantState):
    app_logger.info("INSIDE vector_retrieval NODE")
    query = state["rewritten_query"]
    model = state["selected_model"]
    filtering = {
        "$and": [
            {"brand": {"$eq": model["brand"].split('-')[0]}},
            {"model": {"$eq": model["brand"].split('-')[1]}}
        ]
    }
    chunks = aws_client.query_db(
        query,
        filtering,
        cache=state
    )
    app_logger.info(f"Retrieved chunks: {chunks}")
    return {
        "retrieved_chunks": chunks
    }

def grade_chunks(state):
    """
    Grades retrieved document chunks for relevance to the user query. It returns only the
    chunks that are considered relevant based on the model response.
    Args:
        state: The assistant state containing the user query and retrieved chunks.
    Returns:
        dict: A dictionary with a single key "relevant_chunks" mapping to a list of relevant
        document chunks.
    """
    app_logger.info("INSIDE grade_chunks NODE")
    chunks = state.get("retrieved_chunks", [])
    chunk_string = '\n'.join([f"{i}. {c}" for i, c in enumerate(chunks)])
    prompt = config.prompts['grade_chunks_prompt'].format(query=state["query"], chunk_string=chunk_string)
    result = llm.invoke(prompt)
    try:
        indices = json.loads(result.content)
    except Exception:
        indices = []
    relevant = [chunks[i] for i in indices if i < len(chunks)]
    chunks_string = '\n- '+'\n- '.join(relevant)
    app_logger.info(f"Chunks after filtering: {chunks_string}")
    return {"relevant_chunks": relevant}

def answer_generation(state: AssistantState):
    app_logger.info("INSIDE answer_generation NODE")
    context = "" if "relevant_chunks" not in state else "\n".join(state["relevant_chunks"])
    prompt = config.prompts['answer_prompt'].format(context=context, query=state["query"], language=config.language)
    result = llm.invoke(prompt)
    app_logger.info(f"Answer: {result.content}")
    answer = result.content if 'selected_model' not in state else\
        f"Encontré la respuesta para la motocicleta {state['selected_model']['brand'].upper()}:  \n{result.content}"
    return {"answer": answer}

def grounding_validator(state):
    if "relevant_chunks" not in state:
        return {
            "validated": True,
            "streamlit_state": True
        }
    app_logger.info("INSIDE grounding_validator NODE")
    context = "\n\n".join(state["relevant_chunks"])
    prompt = f"""Question:
        {state['query']}
        Answer:
        {state['answer']}
        Documents:
        {context}
        Is the answer supported by the documents?
        Answer SUPPORTED or NOT_SUPPORTED.
        """
    result = llm.invoke(prompt)
    if "SUPPORTED" in result.content:
        app_logger.success("Answer validated, the system will respond with the final answer")
        return {
            "validated": True,
            "streamlit_state": True
        }
    return {"validated": False}

def route_domain(state: AssistantState):
    if "HELLO" in state["is_motorcycle_related"]:
        return "answer_generation"
    return "model_extraction" if "TRUE" in state["is_motorcycle_related"] else "out_of_scope"

def retry_generation(state):
    return {
        "retries_generation": state["retries_generation"] + 1
    }

def unknown_answer(state):
    app_logger.info("INSIDE unknown_answer NODE")
    app_logger.warning("No answer found, the agent will respond with no information available")
    return {
        "answer": "No pude encontrar la información solicitada en los manuales."
    }

def route_model(state):
    return "query_rewriter" if state["model_confident"] else "ask_clarification"

def route_retrieval(state):
    return "grade_chunks" if state["retrieved_chunks"] else "unknown_answer"

def route_retrieval_grade(state):
    return "answer_generation" if state["relevant_chunks"] else "unknown_answer"

def route_validation(state):
    if state["validated"]:
        return "final_answer"
    if state["retries_generation"] < 2:
        return "retry_generation"
    return "unknown_answer"






builder = StateGraph(AssistantState)

builder.add_node("domain_guard", domain_guard)
builder.add_node("model_extraction", model_extraction)
builder.add_node("model_resolution", model_resolution)
builder.add_node("ask_clarification", ask_clarification)
builder.add_node("query_rewriter", query_rewriter)
builder.add_node("vector_retrieval", vector_retrieval)
builder.add_node("grade_chunks", grade_chunks)
builder.add_node("answer_generation", answer_generation)
builder.add_node("grounding_validator", grounding_validator)
builder.add_node("retry_generation", retry_generation)
builder.add_node("unknown_answer", unknown_answer)

builder.set_entry_point("domain_guard")

builder.add_conditional_edges(
    "domain_guard",
    route_domain,
    {
        "model_extraction": "model_extraction",
        "out_of_scope": "unknown_answer",
        "answer_generation": "answer_generation"
    }
)

builder.add_edge("model_extraction", "model_resolution")

builder.add_conditional_edges(
    "model_resolution",
    route_model,
    {
        "query_rewriter": "query_rewriter",
        "ask_clarification": "ask_clarification"
    }
)

builder.add_edge("query_rewriter", "vector_retrieval")

builder.add_conditional_edges(
    "vector_retrieval",
    route_retrieval,
    {
        "grade_chunks": "grade_chunks",
        "unknown_answer": "unknown_answer"
    }
)

builder.add_conditional_edges(
    "grade_chunks",
    route_retrieval_grade,
    {
        "answer_generation": "answer_generation",
        "unknown_answer": "unknown_answer"
    }
)

builder.add_edge("answer_generation", "grounding_validator")

builder.add_conditional_edges(
    "grounding_validator",
    route_validation,
    {
        "final_answer": END,
        "retry_generation": "retry_generation",
        "unknown_answer": "unknown_answer"
    }
)

builder.add_edge("retry_generation", "answer_generation")

builder.add_edge("unknown_answer", END)
builder.add_edge("ask_clarification", END)

graph = builder.compile()
