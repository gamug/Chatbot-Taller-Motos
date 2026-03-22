
import os

path = {
    'raw_data': 'input',
    'curated_data': 'output',
    'logs': 'logs'
}

agent = {
    'agent_name': os.getenv("AGENT_NAME"),
    'answer_language': os.environ.get("LANGUAGE", 'spanish'),
    'canonical_brand_score': os.environ.get("CANONICAL_SCORE", 0.7),
    'query_copies': os.environ.get("QUERY_COPIES", 3),
    'folder_size_limit': os.environ.get("FOLDER_SIZE_LIMIT", 20),
    'knowledge_output': os.environ.get("KNOWLEDGE_OUTPUT", 'knowledge_output'),
    'pdf_output': os.environ.get("PDF_OUTPUT", 'pdf_output')
}