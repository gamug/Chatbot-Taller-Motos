import os, sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
import streamlit as st

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
import config
from moto_assistant import assistant_graph


st.set_page_config(page_title="Manual de Motos", page_icon="🏍️")

# ----------------------------
# LLM (cached for performance)
# ----------------------------
@st.cache_resource
def load_assistant_graph():
    return assistant_graph

conversation = load_assistant_graph()

# ----------------------------
# Session state
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [{ "role": "assistant", "content": f"Hola, soy tu asistente {config.agent_name} ¿En qué te puedo ayudar hoy? Proporciona marca, modelo y descripción de la consulta para proceder a ayudarte ☺️"}]

# ----------------------------
# UI
# ----------------------------
st.title("🏍️ Manual de Motos")

# Render previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Native chat input (ENTER sends automatically)
if user_input := st.chat_input("Realiza tu consulta..."):
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Consultando manual..."):
            response = conversation.invoke({
                "query": HumanMessage(content=user_input),
                "messages": [],
                "context": "",
                "intent": "",
                "brand_model": ""
            })

            assistant_reply = response["messages"][-1].content
            st.markdown(assistant_reply)

    st.session_state.messages.append({
        "role": "assistant",
        "content": assistant_reply
    })