import os
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Manual de Motos", page_icon="🏍️")

# ----------------------------
# LLM (cached for performance)
# ----------------------------
@st.cache_resource
def get_conversation_chain():
    llm = ChatOpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        model=os.environ["DEEPSEEK_MODEL"],
        base_url=os.environ["DEEPSEEK_URL"],
        temperature=0.7,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant specialized in motorcycle manuals."),
        ("human", "{input}")
    ])

    chain = prompt | llm

    store = {}

    def get_session_history(session_id: str):
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]

    conversation = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )

    return conversation


conversation = get_conversation_chain()

# ----------------------------
# Session state
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

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
            response = conversation.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": "user1"}}
            )

            assistant_reply = response.content
            st.markdown(assistant_reply)

    st.session_state.messages.append({
        "role": "assistant",
        "content": assistant_reply
    })