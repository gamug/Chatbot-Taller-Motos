import os, sys, queue, threading, time
from typing import Any
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
import src.config as config
from src.agents import build_orchestrator_agent
from ui.ui_components import GenericChat
from ui.utils import render_messages

st.set_page_config(page_title="Manual de Motos", page_icon="🏍️")

# --- Session state ---
if "messages" not in st.session_state:
    st.session_state.chat = GenericChat()
    st.session_state.messages = [{"role": "assistant", "content": f"Hola, soy tu asistente {config.agent['agent_name']} ¿En qué te puedo ayudar hoy?"}]
if "downloads" not in st.session_state:
    st.session_state.downloads = {}

# --- Render previous messages ---
render_messages()

# --- Chat input ---
if st.session_state.chat.receive_input():
    st.session_state.chat.place_widgets()
    st.session_state.chat.call_agent()
    st.session_state.chat.token_stream()
    st.session_state.chat.show_downloads()