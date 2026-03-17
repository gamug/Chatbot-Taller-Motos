from typing import TypedDict, List, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.graph import StateGraph, END

import config
from src import app_logger
from commons import get_llm, AWSClient
from src.tools.tools import extract_moto_models


# --------------------------------------
# State
# --------------------------------------

class AssistantState(TypedDict):
    query: HumanMessage
    messages: List[BaseMessage]
    context: str
    intent: Literal["VALID", "INVALID", "GREETINGS", "END"]
    brand_model: dict


# --------------------------------------
# LLM and AWS
# --------------------------------------

llm = get_llm()
llm_with_tools = llm.bind_tools([])
aws_client = AWSClient()


# --------------------------------------
# Prompts
# --------------------------------------

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", config.prompts["chat_prompt"])
])

retrieval_prompt = ChatPromptTemplate.from_messages([
    ("system", config.prompts["retriever_prompt"])
])

intent_prompt = ChatPromptTemplate.from_messages([
    ("system", config.prompts["intent_prompt"]),
    ("human", "{query}")
])

greetings_prompt = ChatPromptTemplate.from_messages([
    ("system", config.prompts["greetings_prompt"].format(
        assistant_name=config.agent_name)),
    MessagesPlaceholder("messages")
])

wrong_intent_prompt = ChatPromptTemplate.from_messages([
    ("system", config.prompts["invalid_prompt"]),
    MessagesPlaceholder("messages")
])


# --------------------------------------
# Intent Node
# --------------------------------------

def intent_node(state: AssistantState):
    app_logger.info("="*20)
    app_logger.info("INSIDE intent NODE")
    app_logger.info("New question sent")
    app_logger.info(f"Question: {state['query'].content}")
    state["messages"].append(state["query"])
    result = llm.invoke(
        intent_prompt.invoke({
            "query": state["query"].content
        })
    ).content.strip()
    app_logger.info(f"Intent: {result}")
    return {
        "intent": result
    }


# --------------------------------------
# Brand Model Extraction Node
# --------------------------------------

def brand_model_node(state: AssistantState):
    app_logger.info("INSIDE brand_model NODE")
    last = state["messages"][-1].content
    result = extract_moto_models(last)
    app_logger.info(f"Result of brand-logo: {result}")
    return {
        "brand_model": result
    }


# --------------------------------------
# Retriever Node
# --------------------------------------

def retrieve_node(state: AssistantState):
    app_logger.info("INSIDE retrieve NODE")
    brand_model = state.get("brand_model", {})
    filtering = {
        "$and": [
            {"brand": {"$eq": brand_model["brand"]}},
            {"model": {"$eq": brand_model["model"]}}
        ]
    }
    app_logger.info(f"Retriever will use as filter in the s3-verctors: {filtering}")
    context = aws_client.query_db(
        brand_model["query"],
        filtering
    )
    context = "\n".join([text.replace("\n", " ").strip() for text in context])
    log_text = context.replace('\n', ' - ')
    app_logger.info(f"Context got from database: {log_text}")
    if not context:
        app_logger.warning("Retriever not found relevant information to answer the user answer: the agent will refuses to answer the query")
        return {"context": "Not context found"}
    context = llm.invoke(
        retrieval_prompt.invoke({
            "query": brand_model["query"],
            "context": context
        })
    ).content.strip()
    log_text = context.replace('\n', ' - ')
    app_logger.info(f"content preserved after LLM filtering: {log_text}")
    return {"context": context}


# --------------------------------------
# Response Node
# --------------------------------------

def response_node(state: AssistantState):
    intent = state["intent"]
    if intent == "INVALID":
        app_logger.info("Intent was INVALID and for that reason agent will raise a warning...")
        response = llm_with_tools.invoke(
            wrong_intent_prompt.invoke({
                "messages": state["messages"]
            })
        )
    elif intent == "VALID":
        brand_model = state.get("brand_model")
        if brand_model and brand_model['query']:
            if len(state["context"]):
                app_logger.success("Let's make the user happy...")
            else:
                app_logger.info("No context found for the user query")
            response = llm_with_tools.invoke(
                chat_prompt.invoke({
                    "assistant_name": config.agent_name,
                    "query": state["brand_model"]["query"],
                    "context": state["context"]
                })
            )
        if not brand_model:
            app_logger.info("The agent was unable to extract brand and model")
            response = AIMessage(
                content=(
                    "No pude identificar la marca y modelo de motocicleta en tu consulta. Por favor proporciona tanto la marca como el modelo, no olvides la pregunta de nuevo 😉"
                )
            )
        if not brand_model['query']:
            app_logger.info("The agent was unable to extract user query")
            response = AIMessage(
                content=(
                    "Pude entender la marca y el modelo pero no hay una pregunta clara en tu consulta ¿Podrías ser claro sobre lo que quieres consultar en los manuales?q"
                )
            )
    else:  # greetings
        app_logger.success("User want to be nice, let's be nice too...")
        response = llm_with_tools.invoke(
            greetings_prompt.invoke({
                "messages": state["messages"]
            })
        )

    state["messages"].append(response)
    return {"messages": state["messages"]}


# --------------------------------------
# Routers
# --------------------------------------

def intent_router(state: AssistantState):
    intent = state["intent"]
    if intent == "END":
        return "end"
    if intent in ["INVALID", "GREETINGS"]:
        return "respond"
    return "brand"


def brand_model_router(state: AssistantState):
    brand_model = state.get("brand_model", {})
    if brand_model and brand_model['query']:
        return "retrieve"
    if not brand_model:
        app_logger.warning("Agent was unable to get brand-model, the system will respond asking for user clarification")
    if brand_model and not brand_model['query']:
        app_logger.warning("Agent was unable to get the user question, the system will respond asking for user clear query")
    return "respond"


# --------------------------------------
# Graph
# --------------------------------------

graph = StateGraph(AssistantState)

graph.add_node("intent", intent_node)
graph.add_node("brand_model", brand_model_node)
graph.add_node("retrieval", retrieve_node)
graph.add_node("response_node", response_node)

graph.set_entry_point("intent")


graph.add_conditional_edges(
    "intent",
    intent_router,
    {
        "respond": "response_node",
        "brand": "brand_model",
        "end": END
    }
)


graph.add_conditional_edges(
    "brand_model",
    brand_model_router,
    {
        "retrieve": "retrieval",
        "respond": "response_node"
    }
)


graph.add_edge("retrieval", "response_node")


assistant_graph = graph.compile()