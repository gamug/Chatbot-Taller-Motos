import os, sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
import streamlit as st

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
import config
from moto_assistant import graph


# ----------------------------
# graph (cached for performance)
# ----------------------------
@st.cache_resource
def load_assistant_graph():
    return graph

st.set_page_config(page_title="Manual de Motos", page_icon="🏍️")

# ----------------------------
# Session state
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [{ "role": "assistant", "content": f"Hola, soy tu asistente {config.agent_name} ¿En qué te puedo ayudar hoy? Proporciona marca, modelo y descripción de la consulta para proceder a ayudarte ☺️"}]

if "solved" not in st.session_state or st.session_state.solved:
    st.session_state.queries = []
    st.session_state.solved = False
    st.session_state.conversation = load_assistant_graph()

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
            st.session_state.queries.append(user_input)
            query = 'Message history: \n -' + '\n -'.join(st.session_state.queries)
            response = st.session_state.conversation.invoke({
                "query": query,
                "retries_generation": 0,
                "embedding_cache": {},
                "streamlit_state": False
            })
            st.markdown(response["answer"])
            
    # Update session state
    st.session_state.solved = response["streamlit_state"]

    st.session_state.messages.append({
        "role": "assistant",
        "content": response["answer"]
    })