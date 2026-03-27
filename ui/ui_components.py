import os, queue, threading, time
from typing import Any, Callable
from src.agents import build_orchestrator_agent
import streamlit as st

@st.dialog("Memoria del chatbot")
def confirm_dialog():
    st.write("Existe información en la memoria del chatbot ¿Desea cargarla?\n\nSi decide no cargala la información se perderá.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Si"):
            st.session_state.confirmed = True
            st.rerun()
    with col2:
        if st.button("No"):
            st.session_state.confirmed = False
            st.rerun()


class GenericChat:
    """
    Manages the motorcycle manual chatbot interaction flow.
    Steps: receive input → place widgets → call agent → token stream → show downloads
    """

    def __init__(self):
        self.user_input: str | None = None
        self.msg_index: int | None = None
        self.start_time: float | None = None
        self.elapsed: float = 0.0

        # Widget containers
        self.col2 = None
        self.timer_placeholder = None
        self.log_placeholder = None
        self.text_placeholder = None

        # Queues and threading
        self.q: queue.Queue = queue.Queue()
        self.text_q: queue.Queue = queue.Queue()
        self.download_q: queue.Queue = queue.Queue()
        self.done_event: threading.Event = threading.Event()

        # Data containers
        self.result_container: dict[str, Any] = {"response": None}
        self.logs: list[str] = []
        self.streamed_text: str = ""
        self.generated_files: list[str] = []

    def receive_input(self) -> bool:
        """Step 1: Receive user input from chat interface."""
        self.user_input = st.chat_input("Realiza tu consulta...")

        if self.user_input is None:
            return False

        # Display user message
        with st.chat_message("user"):
            st.markdown(self.user_input)

        # Store in session state and track message index
        st.session_state.messages.append({"role": "user", "content": self.user_input})
        self.msg_index = len(st.session_state.messages)

        return True

    def place_widgets(self) -> None:
        """Step 2: Create and position all UI elements for the response."""
        with st.chat_message("assistant"):
            self.col1, self.col2 = st.columns([3, 1])

            with self.col1:
                st.markdown("**🔍 Consultando manual...**")

            with self.col2:
                self.timer_placeholder = st.empty()

            with st.expander("📋 Ver proceso", expanded=True):
                self.log_placeholder = st.empty()

            self.text_placeholder = st.empty()

        self.start_time = time.time()

    def call_agent(self) -> None:
        """Step 3: Execute the agent in a separate thread."""
        def run_agent():

            agent = build_orchestrator_agent(
                self.q, self.text_q, self.download_q, self.done_event
            )
            self.result_container["response"] = agent(self.user_input)
            self.q.put("__DONE__")

        thread = threading.Thread(target=run_agent)
        thread.start()
        self.thread = thread

    def token_stream(self) -> None:
        """Step 4: Stream tokens, logs, and handle queue processing."""
        while True:
            self.elapsed = time.time() - self.start_time
            self.timer_placeholder.markdown(f"⏱️ `{self.elapsed:.1f}s`")

            # Process log events
            try:
                event = self.q.get(timeout=0.1)
                if event == "__DONE__":
                    break
                self.logs.append(event)
                self.log_placeholder.markdown("\n\n".join(self.logs))
            except queue.Empty:
                pass

            # Stream text tokens (only if answer not frozen)
            if not self.done_event.is_set():
                while not self.text_q.empty():
                    chunk = self.text_q.get()
                    self.streamed_text += chunk
                    self.text_placeholder.markdown(self.streamed_text)

            # Collect generated files
            while not self.download_q.empty():
                self.generated_files.append(self.download_q.get())

        # Wait for thread to complete
        self.thread.join()

        # Final render and session state update
        total_time = time.time() - self.start_time
        self.timer_placeholder.markdown(f"⏱️ Completado en `{total_time:.1f}s`")
        self.text_placeholder.markdown(self.streamed_text)
        st.session_state.messages.append({"role": "assistant", "content": self.streamed_text})

    def show_downloads(self) -> None:
        """Step 5: Display download buttons for generated files."""
        if not self.generated_files:
            return

        st.session_state.downloads[self.msg_index] = self.generated_files

        for pdf_path in self.generated_files:
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label=f"📄 Descargar {os.path.basename(pdf_path)}",
                    data=f.read(),
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                    key=f"download_{self.msg_index}_{pdf_path}",
                )

    def run(self) -> None:
        """Execute the full interaction flow."""
        if not self.receive_input():
            return

        self.place_widgets()
        self.call_agent()
        self.token_stream()
        self.show_downloads()