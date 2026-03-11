import json
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


import config
from commons import AWSClient, get_llm

aws_client = AWSClient()
llm = get_llm()


def search_knowledge(query: str):
    """Tool to search in the knowledge base (vector database) using the AWS client. It takes a query as input and returns
    the relevant context from the database that can be used to answer the user's question.
    Args:
        query (str): The user's question or query that needs to be answered based on the motorcycle manuals.
    Returns:
        str: The relevant context retrieved from the knowledge base that can be used to answer the user's question.
    """
    return aws_client.query_db(query)


def extract_moto_models(text: str) -> dict:
    """Tool to extract motorcycle brand and model information from the provided text. It uses a language model (LLM)
    to analyze the input text and identify any mentions of motorcycle brands and models. The output is a dictionary
    containing the extracted information, including the text where the brand and model were mentioned, the identified
    brand, and the identified model. If no motorcycle brand is mentioned in the input text, it returns an empty dictionary.
    Args:
        text (str): The input text that may contain mentions of motorcycle brands and models.
    Returns:
        dict: A dictionary containing the extracted motorcycle brand and model information. The dictionary has the following structure:
            {
                'text': str,  # The text where the brand and model were mentioned
                'brand': str, # The identified motorcycle brand
                'model': str  # The identified motorcycle model
                'query': str  # The user query without the brand and model information
            }
            If no motorcycle brand is mentioned in the input text, it returns an empty dictionary.
    """
    moto_models = ChatPromptTemplate.from_messages([
        ("system", config.prompts["moto_models_prompt"]),
        MessagesPlaceholder(variable_name="input")
    ])

    result = llm.invoke(
            moto_models.invoke({"input": [("human", text)]})
        )
    return {key: value.lower() for key, value in json.loads(result.content).items()}

# tools = [search_knowledge, extract_moto_models]