import os, sys
import queue
import threading
import time
# inject download queue into tool

from dotenv import load_dotenv
import streamlit as st

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
import config
import agents as agents_module

st.set_page_config(page_title="Manual de Motos", page_icon="🏍️")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"Hola, soy tu asistente {config.agent['agent_name']} ¿En qué te puedo ayudar hoy? Proporciona marca, modelo y descripción de la consulta para proceder a ayudarte ☺️"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

class StreamlitCallbackHandler:
    def __init__(self, q: queue.Queue, text_q: queue.Queue, download_q: queue.Queue):
        self.q = q
        self.text_q = text_q
        self.download_q = download_q
        self.current_tool = None
        self.tool_executing = False

    def __call__(self, **kwargs):
        event = kwargs.get("event", {})

        text = event.get("contentBlockDelta", {}).get("delta", {}).get("text", "")
        if text:
            self.text_q.put(text)
            return

        tool_use = event.get("contentBlockStart", {}).get("start", {}).get("toolUse", {})
        if tool_use:
            self.current_tool = tool_use.get("name", "tool")
            self.tool_executing = True
            self.q.put(f"⚙️ Ejecutando: `{self.current_tool}`...")
            return

        if "messageStart" in event and self.tool_executing:
            self.tool_executing = False
            self.q.put(f"✅ `{self.current_tool}` completado")
            self.current_tool = None
            return

if user_input := st.chat_input("Realiza tu consulta..."):
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**🔍 Consultando manual...**")
        with col2:
            timer_placeholder = st.empty()

        with st.expander("📋 Ver proceso", expanded=True):
            log_placeholder = st.empty()

        text_placeholder = st.empty()
        download_placeholder = st.empty()  # download button goes here

        result_container = {"response": None}
        q = queue.Queue()
        text_q = queue.Queue()
        download_q = queue.Queue()
        start_time = time.time()
        agents_module._download_q = download_q

        def run_agent():
            handler = StreamlitCallbackHandler(q, text_q, download_q)
            result_container["response"] = agents_module.orchestrator_agent(user_input, callback_handler=handler)
            q.put("__DONE__")

        thread = threading.Thread(target=run_agent)
        thread.start()

        logs = []
        streamed_text = ""
        while True:
            elapsed = time.time() - start_time
            timer_placeholder.markdown(f"⏱️ `{elapsed:.1f}s`")

            try:
                event = q.get(timeout=0.1)
                if event == "__DONE__":
                    break
                logs.append(event)
                log_placeholder.markdown("\n\n".join(logs))
            except queue.Empty:
                pass

            while not text_q.empty():
                chunk = text_q.get()
                streamed_text += chunk
                text_placeholder.markdown(streamed_text)

            # check for download files
            while not download_q.empty():
                pdf_path = download_q.get()
                with open(pdf_path, "rb") as f:
                    download_placeholder.download_button(
                        label="📄 Descargar PDF",
                        data=f.read(),
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf"
                    )

        thread.join()

        total = time.time() - start_time
        timer_placeholder.markdown(f"⏱️ Completado en `{total:.1f}s`")
        text_placeholder.markdown(str(result_container["response"]))

    st.session_state.messages.append({"role": "assistant", "content": str(result_container["response"])})