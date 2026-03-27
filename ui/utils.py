import os
import streamlit as st

def render_messages():
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if i in st.session_state.downloads:
                for html_path in st.session_state.downloads[i]:
                    if os.path.exists(html_path):
                        with open(html_path, "rb") as f:
                            st.download_button(
                                label=f"📄 Descargar {os.path.basename(html_path)}",
                                data=f.read(),
                                file_name=os.path.basename(html_path),
                                mime="text/html",
                                key=f"download_{i}_{html_path}"
                            )