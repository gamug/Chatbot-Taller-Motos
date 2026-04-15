import os
import sys
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
import src.config as config
from ui.ui_components import GenericChat
from ui.utils import render_messages

st.set_page_config(page_title="Manual de Motos", page_icon="🏍️")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": f"Hola, soy tu asistente {config.agent['agent_name']} ¿En qué te puedo ayudar hoy?",
        }
    ]

if "downloads" not in st.session_state:
    st.session_state.downloads = {}

if "chat_is_streaming" not in st.session_state:
    st.session_state.chat_is_streaming = False
if "chat_logs" not in st.session_state:
    st.session_state.chat_logs = []
if "chat_text" not in st.session_state:
    st.session_state.chat_text = ""
if "chat_files" not in st.session_state:
    st.session_state.chat_files = []
if "chat_done" not in st.session_state:
    st.session_state.chat_done = False
if "response_container" not in st.session_state:
    st.session_state.response_container = None

# Render previous messages
render_messages()

# Run chat
chat = GenericChat()
chat.run()