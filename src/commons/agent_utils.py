import difflib, json
import pandas as pd
from typing import List, Optional, TypedDict
from langchain_openai import ChatOpenAI

import config


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

def extract_moto_models(query:str, llm: ChatOpenAI, brands: dict[str, dict]) -> List[dict]:
    result = llm.invoke(config.prompts['moto_models_prompt'].format(query=query))
    result = json.loads(result.content)
    motorcycle = f"{result['brand'].lower()}-{result['model'].lower()}"
    motorcycles = [dict_['motorcycle'] for dict_ in brands.values()]
    matches_ratio = [difflib.SequenceMatcher(None, motorcycle, dict_['motorcycle']).ratio() for dict_ in brands.values()]
    df = pd.DataFrame({'brand': motorcycles, 'score': matches_ratio})
    return df.sort_values(by='score', ascending=False).reset_index(drop=True).head(5).to_dict('records')