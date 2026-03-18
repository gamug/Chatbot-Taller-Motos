from typing import List, Optional, TypedDict
import streamlit as st

class AssistantState(TypedDict):
    query: str
    is_motorcycle_related: Optional[bool]
    detected_models: Optional[list]
    selected_model: Optional[dict]
    model_confident: Optional[bool]
    rewritten_query: Optional[str]
    retrieved_chunks: Optional[List[str]]
    relevant_chunks: Optional[List[str]]
    answer: Optional[str]
    retries_retrieval: int
    retries_generation: int
    embedding_cache: dict
    streamlit_state: st.session_state