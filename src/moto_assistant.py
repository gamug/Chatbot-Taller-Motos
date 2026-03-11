from typing import TypedDict, List, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.graph import StateGraph, END

import config
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
    state["messages"].append(state["query"])
    result = llm.invoke(
        intent_prompt.invoke({
            "query": state["query"].content
        })
    )
    return {
        "intent": result.content.strip()
    }


# --------------------------------------
# Brand Model Extraction Node
# --------------------------------------

def brand_model_node(state: AssistantState):
    last = state["messages"][-1].content
    result = extract_moto_models(last)
    return {
        "brand_model": result
    }


# --------------------------------------
# Retriever Node
# --------------------------------------

def retrieve_node(state: AssistantState):
    brand_model = state.get("brand_model", {})
    if not brand_model:
        return {"context": ""}
    filtering = {
        "$and": [
            {"brand": {"$eq": brand_model["brand"]}},
            {"model": {"$eq": brand_model["model"]}}
        ]
    }
    context = aws_client.query_db(
        brand_model["query"],
        filtering
    )
    context = "\n".join([text.replace("\n", " ").strip() for text in context])
    if not context:
        return {"context": "Not context found"}
    context = llm.invoke(
        retrieval_prompt.invoke({
            "query": brand_model["query"],
            "context": context
        })
    ).content.strip()
    return {"context": context}


# --------------------------------------
# Response Node
# --------------------------------------

def response_node(state: AssistantState):
    intent = state["intent"]
    if intent == "INVALID":
        response = llm_with_tools.invoke(
            wrong_intent_prompt.invoke({
                "messages": state["messages"]
            })
        )
    elif intent == "VALID":
        if state.get("brand_model"):
            response = llm_with_tools.invoke(
                chat_prompt.invoke({
                    "assistant_name": config.agent_name,
                    "query": state["brand_model"]["query"],
                    "context": state["context"]
                })
            )
        else:
            response = AIMessage(
                content=(
                    "No pude identificar la marca y modelo de motocicleta en tu consulta. Por favor proporciona tanto la marca como el modelo, no olvides la pregunta de nuevo 😉"
                )
            )
    else:  # greetings
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
    if brand_model:
        return "retrieve"
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