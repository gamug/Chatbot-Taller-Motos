import os
import queue
import threading
import time
from typing import Any
from src.agents import build_orchestrator_agent
import streamlit as st


class GenericChat:
    """
    Fresh approach: Decouple agent execution from UI rendering.
    Uses st.session_state to pass data between background thread and UI.
    Fragment auto-reruns to display updates independently.
    """

    def __init__(self):
        self.user_input: str | None = None
        self.msg_index: int | None = None

    def receive_input(self) -> bool:
        """Step 1: Receive user input."""
        self.user_input = st.chat_input("Realiza tu consulta...")
        if self.user_input is None:
            return False

        with st.chat_message("user"):
            st.markdown(self.user_input)

        st.session_state.messages.append({"role": "user", "content": self.user_input})
        self.msg_index = len(st.session_state.messages)
        
        # Initialize streaming session state
        st.session_state.chat_is_streaming = True
        st.session_state.chat_logs = []
        st.session_state.chat_text = ""
        st.session_state.chat_files = []
        st.session_state.chat_start_time = time.time()
        st.session_state.chat_done = False

        return True

    def place_widgets(self) -> None:
        """Step 2: Create container for response."""
        st.session_state.response_container = st.container()

    def call_agent(self) -> None:
        """Step 3: Start agent in background thread."""
        def agent_worker():
            # Create fresh queues for this run
            q = queue.Queue()
            text_q = queue.Queue()
            download_q = queue.Queue()
            done_event = threading.Event()

            try:
                agent = build_orchestrator_agent(q, text_q, download_q, done_event)
                agent(self.user_input)
            except Exception as e:
                print(f"[AGENT ERROR] {e}")
                import traceback
                traceback.print_exc()

            # Transfer all queue data to session state
            while True:
                try:
                    event = q.get_nowait()
                    if event == "__DONE__":
                        break
                    st.session_state.chat_logs.append(event)
                except queue.Empty:
                    break

            while True:
                try:
                    chunk = text_q.get_nowait()
                    st.session_state.chat_text += chunk
                except queue.Empty:
                    break

            while True:
                try:
                    file_path = download_q.get_nowait()
                    st.session_state.chat_files.append(file_path)
                except queue.Empty:
                    break

            # Mark as done
            st.session_state.chat_done = True

        thread = threading.Thread(target=agent_worker, daemon=True)
        thread.start()

    def display_response(self) -> None:
        """Step 4: Display response with live updates using fragment."""
        @st.fragment(run_every=0.1)
        def live_display():
            """Fragment that updates every 100ms."""
            with st.session_state.response_container:
                with st.chat_message("assistant"):
                    # Columns for layout
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown("**🔍 Consultando manual...**")

                    with col2:
                        # Timer
                        if st.session_state.chat_is_streaming:
                            elapsed = time.time() - st.session_state.chat_start_time
                            st.markdown(f"⏱️ `{elapsed:.1f}s`")
                        else:
                            total = time.time() - st.session_state.chat_start_time
                            st.markdown(f"⏱️ Completado en `{total:.1f}s`")

                    # Logs section
                    with st.expander("📋 Ver proceso", expanded=True):
                        if st.session_state.chat_logs:
                            st.markdown("\n\n".join(st.session_state.chat_logs))
                        else:
                            st.caption("Esperando respuesta...")

                    # Response text
                    if st.session_state.chat_text:
                        st.markdown(st.session_state.chat_text)

                    # Files
                    if st.session_state.chat_done and st.session_state.chat_files:
                        st.divider()
                        for pdf_path in st.session_state.chat_files:
                            try:
                                with open(pdf_path, "rb") as f:
                                    st.download_button(
                                        label=f"📄 Descargar {os.path.basename(pdf_path)}",
                                        data=f.read(),
                                        file_name=os.path.basename(pdf_path),
                                        mime="application/pdf",
                                        key=f"download_{self.msg_index}_{pdf_path}",
                                    )
                            except FileNotFoundError:
                                st.error(f"Archivo no encontrado: {pdf_path}")

            # Stop streaming when agent finishes
            if st.session_state.chat_done:
                st.session_state.chat_is_streaming = False
                # Save message
                if st.session_state.chat_text:
                    st.session_state.messages.append(
                        {"role": "assistant", "content": st.session_state.chat_text}
                    )
                if st.session_state.chat_files:
                    st.session_state.downloads[self.msg_index] = st.session_state.chat_files

        # Display the live fragment
        live_display()

    def run(self) -> None:
        """Execute the full flow."""
        if not self.receive_input():
            return

        self.place_widgets()
        self.call_agent()
        self.display_response()