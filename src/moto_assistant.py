import json
from langgraph.graph import StateGraph, END

from src.commons import (
    AWSClient, get_brands, get_llm, extract_moto_models
)
from src.types.state import AssistantState


brands = get_brands()
llm = get_llm()
aws_client = AWSClient()

def domain_guard(state: AssistantState):
    prompt = f"""
    Determine if the query is about motorcycles.
    Query: {state['query']}
    Answer ONLY TRUE or FALSE.
    """
    result = llm.invoke(prompt)
    return {
        "is_motorcycle_related": "TRUE" in result.content.upper()
    }

def ask_clarification(state):
    models = state["detected_models"]
    options = [m['brand'] for m in models]
    return {
        "answer": f"Which motorcycle do you mean? {options}"
    }

def model_extraction(state: AssistantState):
    """
    Extracts the motorcycle models from the user query.
    Args:
        state: AssistantState
    Returns:
        dict: A dictionary containing the detected motorcycle models.
    """
    models = extract_moto_models(state["query"], llm, brands)
    return {"detected_models": models}

def model_resolution(state: AssistantState):
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
    model = state["selected_model"]
    prompt = f"""
    Rewrite the query to improve search in a motorcycle manual.
    Motorcycle: {model['brand']}
    User query: {state['query']}
    Provide the rewritten query without introductory text or additional comments.
    Provide a single version, the best for the query.
    """
    result = llm.invoke(prompt)
    return {
        "rewritten_query": result.content
    }

def vector_retrieval(state: AssistantState):
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
    chunks = state.get("retrieved_chunks", [])
    prompt = f"""
        You are filtering relevant documents.
        Question:
        {state['query']}
        Documents:
        {chr(10).join([f"{i}. {c}" for i, c in enumerate(chunks)])}
        Return a list of relevant document indices (e.g., [0,2,3]).
        """
    result = llm.invoke(prompt)
    try:
        indices = json.loads(result.content)
    except Exception:
        indices = []
    relevant = [chunks[i] for i in indices if i < len(chunks)]
    return {"relevant_chunks": relevant}

def retry_retrieval(state):
    return {
        "retries_retrieval": state["retries_retrieval"] + 1
    }

def answer_generation(state: AssistantState):
    context = "\n\n".join(state["relevant_chunks"])
    prompt = f"""Answer the question using ONLY the context.
            Context:
            {context}
            Question:
            {state['query']}
            In case there isn't enough context, return "No pude encontrar la información solicitada en los manuales."
            Answer ONLY in spanish
            """
    result = llm.invoke(prompt)
    return {"answer": result.content}

def grounding_validator(state):
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
        return {"validated": True}
    return {"validated": False}

def route_domain(state: AssistantState):
    return "model_extraction" if state["is_motorcycle_related"] else "out_of_scope"

def retry_generation(state):
    return {
        "retries_generation": state["retries_generation"] + 1
    }

def unknown_answer(state):
    return {
        "answer": "I could not find this information in the motorcycle manual."
    }

def route_model(state):
    return "query_rewriter" if state["model_confident"] else "ask_clarification"

def route_retrieval(state):
    if state["relevant_chunks"]:
        return "answer_generation"
    if state["retries_retrieval"] < 2:
        return "retry_retrieval"
    return "unknown_answer"

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
builder.add_node("retry_retrieval", retry_retrieval)
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
        "out_of_scope": "unknown_answer"
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
builder.add_edge("vector_retrieval", "grade_chunks")

builder.add_conditional_edges(
    "grade_chunks",
    route_retrieval,
    {
        "answer_generation": "answer_generation",
        "retry_retrieval": "retry_retrieval",
        "unknown_answer": "unknown_answer"
    }
)

builder.add_edge("retry_retrieval", "vector_retrieval")

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
