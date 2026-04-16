# Ecta Chatbot


## Description
The Ecta Chatbot is an agent‑based conversational system designed to support a motorcycle repair shop by answering customer inquiries about motorcycle maintenance, repairs, and service information. Its core functionality revolves around processing a PDF database of motorcycle manuals, extracting technical knowledge, and using that knowledge to generate natural‑language responses.

The architecture follows an orchestration pattern with three main components:

<ul>
<li><b>Orchestrator</b> – directs the flow of conversation, decides which specialized agent handles each step, and determines when to stop the interaction. It ensures the final answer is a high‑quality, technically rich response in markdown format.</li>
<li><b>Retriever</b> – searches a vector database (stored in AWS S3) for relevant document chunks based on the user’s question. It uses LangChain for document processing and embedding‑based similarity search.</li>
<li><b>Generator</b> – synthesizes the retrieved information into a coherent, detailed answer, expanding on related technical details found in the knowledge base.</li>
</ul>

The chatbot’s workflow includes:

1. Understanding the user’s question.
2. Extracting the motorcycle brand and model from the query.
3. Determining the canonical form of the brand‑model.
4. Rewriting the question in a clear, technical manner.
5. Querying the knowledge database for relevant chunks.
6. Enriching the retrieved chunks with additional context.
7. Generating a final response that not only answers the question but also provides supplementary technical information from the manuals.

The system is built with Python, leveraging the Strands framework for agent construction, LangChain for document loading and vector‑store management, and Streamlit for the web interface. Environment configuration is handled via dotenv, and the project is structured into modular source directories (e.g., `src/agents`, `src/config`) to separate concerns such as agent logic, configuration, and utility functions.

### process_db.py
The `process_db.py` module is responsible for processing PDF manuals to extract text, split it into manageable chunks, and create vector embeddings that are stored in an AWS S3-based vector database for efficient retrieval. This module forms the core of the knowledge base ingestion pipeline for the Ecta Chatbot.

**Key Functions:**
<ul>
<li><b>PDF Text Extraction:</b> Extracts raw text from PDF files using a PDF parser.</li>
<li><b>Text Chunking:</b> Splits the extracted text into smaller, semantically meaningful chunks using a recursive character text splitter. This ensures that each chunk is of an appropriate size for embedding generation and retrieval.</li>
<li><b>Metadata Generation:</b> For each chunk, metadata is created including the source file name, page number, chunk index, and brand-model information (derived from a predefined mapping). This metadata is preserved and stored alongside the vector embeddings.</li>
<li><b>Vector Embedding Creation:</b> Converts each text chunk into a vector embedding using a sentence transformer model (e.g., `all-MiniLM-L6-v2`). These embeddings capture the semantic meaning of the text.</li>
<li><b>AWS S3 Vector Storage:</b> Stores the generated vector embeddings and their associated metadata in an AWS S3 bucket configured as a vector database. The module uses the `aws_client` to handle the insertion of vectors into the S3 service.</li>
<li><b>JSON Output:</b> Additionally, the processed chunks and metadata are saved locally as a JSON file for backup and debugging purposes. The output path is constructed based on the input file's directory structure.</li>
</ul>

**AWS S3 Vector Service Integration:**
The project utilizes AWS S3 as the vector database. The service is accessed via a custom client (`aws_client`) which handles:
<ul>
<li>Connecting to the specified S3 bucket.</li>
<li>Storing vector embeddings and metadata in a structured format within the bucket.</li>
<li>Enabling efficient similarity search and retrieval of vectors based on query embeddings.</li>
</ul>

The integration ensures that the chatbot can quickly retrieve relevant information from the stored knowledge base by performing vector similarity searches against the embeddings stored in S3.

**Code Example (from context):**
```python
# Extract and clean text from PDF pages
metadatas = [re.sub('(\n* *\n)+', '\n', page) for page in text]
metadatas = [re.sub(' +', ' ', page).strip().lower() for page in metadatas]
# Split text into chunks
metadatas = [[re.sub('\n', ' ', chunk) for chunk in splitter.split_text(page) if len(chunk)>20] for page in metadatas]
# Add brand-model metadata
brand_model = brands[file.split('.')[0]]
del brand_model['manual']
metadatas = [{
    'file': file,
    'text': chunk,
    'page': i+1,
    'chunk': j+1,
    'type': 'text'
    }|brand_model for i, page in enumerate(metadatas) for j, chunk in enumerate(page) if len(page)]
texts = [chunk['text'] for chunk in metadatas]
# Insert vectors into AWS S3
aws_client.insert_vectors(texts, metadatas)
# Save metadata locally as JSON
output_path = get_output_path(base_path, file)
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(metadatas, f, ensure_ascii=False, indent=4, default=str)
```

**Metadata Preservation:**
The module strictly preserves the `file` metadata key without modification, ensuring traceability back to the original PDF source. All chunks retain their `file` and `page` metadata, which are referenced in subsequent retrieval and enrichment steps.

### src/data_processing/pdf_processing.py
```python
import fitz, json, os, pytesseract, re
from typing import Any

from commons.utils import get_output_path, get_nlp_tools, process_image
from commons.utils import get_brands
from commons import AWSClient

pytesseract.pytesseract.tesseract_cmd = os.environ['TESSERACT_PATH']

splitter, aws_client = get_nlp_tools(), AWSClient()

def process_pdf(text: list[str], base_path: str, file: str, brands: dict[str, dict[str, str]]) -> None:
    """Processes a single pdf file.

    Args:
        text (list[str]): The text extracted from the pdf file.
        base_path (str): The path to the pdf file.
        file (str): The name of the pdf file.
        brands (dict[dict[str, str]]): The relation between file and brand-model.

    Returns:
        None"""
    metadatas = [re.sub('(\n* *\n)+', '\n', page) for page in text]
    metadatas = [re.sub(' +', ' ', page).strip().lower() for page in metadatas]
    metadatas = [[re.sub('\n', ' ', chunk) for chunk in splitter.split_text(page) if len(chunk)>20] for page in metadatas]
    brand_model = brands[file.split('.')[0]]
    del brand_model['manual']
    metadatas = [{
        'file': file,
        'text': chunk,
        'page': i+1,
        'chunk': j+1,
        'type': 'text'
        }|brand_model for i, page in enumerate(metadatas) for j, chunk in enumerate(page) if len(page)]
    texts = [chunk['text'] for chunk in metadatas]
    aws_client.insert_vectors(texts, metadatas)
    output_path = get_output_path(base_path, file)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadatas, f, ensure_ascii=False, indent=4, default=str)
```

This module handles PDF processing for the Ecta Chatbot's knowledge base. It extracts text from PDF files, chunks it into manageable segments, and stores vector representations in Amazon S3 for semantic search capabilities.

## Key Components

### 1. **PDF Text Processing Pipeline**
<ul>
<li><strong>Text Normalization</strong>: Removes excessive whitespace and newlines using regex patterns</li>
<li><strong>Case Normalization</strong>: Converts all text to lowercase for consistency</li>
<li><strong>Text Chunking</strong>: Splits pages into meaningful chunks using NLP tools (minimum 20 characters)</li>
<li><strong>Metadata Enrichment</strong>: Adds file, page, chunk, and type information to each segment</li>
</ul>

### 2. **Brand-Model Integration**
The module integrates with brand-model data from the `get_brands()` function to associate each PDF with specific motorcycle brands and models. The `brand_model` dictionary is merged with chunk metadata, excluding the 'manual' key.

### 3. **Amazon S3 Vector Storage**
The module uses `AWSClient.insert_vectors()` to store vector representations in Amazon S3. This service provides:
<ul>
<li><strong>Scalable Storage</strong>: Handles large volumes of vector embeddings</li>
<li><strong>Semantic Search</strong>: Enables similarity-based retrieval for chatbot queries</li>
<li><strong>Metadata Preservation</strong>: Maintains file, page, and chunk information alongside vectors</li>
</ul>

### 4. **Output Generation**
Processed chunks are saved as JSON files with the following structure:
```json
{
    "file": "manual.pdf",
    "text": "extracted chunk content",
    "page": 1,
    "chunk": 1,
    "type": "text",
    "brand": "Honda",
    "model": "CBR600RR"
}
```

### 5. **Image Processing Support**
For PDFs containing only images, the module relies on:
<ul>
<li><strong>Tesseract OCR</strong>: Configured via `TESSERACT_PATH` environment variable</li>
<li><strong>Image Processing Utilities</strong>: Available through `process_image()` function</li>
<li><strong>Text Extraction</strong>: Converts image content to searchable text</li>
</ul>

## Amazon S3 Vector Service Integration
The project uses Amazon S3 for vector storage with the following characteristics:

<table>
<tr><th>Feature</th><th>Description</th><th>Implementation</th></tr>
<tr><td>Vector Storage</td><td>Stores embeddings for semantic search</td><td><code>AWSClient.insert_vectors()</code></td></tr>
<tr><td>Metadata Association</td><td>Links vectors to source documents</td><td>Chunk metadata preserved in S3</td></tr>
<tr><td>Scalability</td><td>Handles large document collections</td><td>Cloud-native architecture</td></tr>
<tr><td>Retrieval</td><td>Enables similarity search for chatbot</td><td>Used by query agents</td></tr>
</table>

## Processing Flow
1. **Input**: PDF file with associated brand-model mapping
2. **Extraction**: Text or OCR-based content extraction
3. **Chunking**: NLP-based segmentation into meaningful units
4. **Vectorization**: Conversion to embeddings stored in S3
5. **Output**: JSON metadata file and S3 vector database entries

The module ensures all processed content is searchable through the chatbot's knowledge retrieval system while maintaining traceability back to original source documents via the preserved `file` metadata key.

### src/commons/llm_utils.py
The `src/commons/llm_utils.py` module contains the `AWSClient` class, which handles interactions with AWS S3 vector database services. This class is central to managing vector data for the chatbot, providing methods to create a bucket, upload vectors, retrieve vectors, and delete vectors.

The AWS S3 vector service used in this project is a managed vector database solution that stores vector embeddings alongside metadata in S3 buckets. It enables efficient similarity search and retrieval for AI applications. The service is accessed via the AWS SDK, with configuration parameters stored in environment variables.

Key methods in `AWSClient` include:

<ul><li><code>store_vectors_with_progress</code>: Uploads vectors in batches with a progress bar, using <code>s3_client.put_vectors</code> to store vectors in the specified index.</li><li><code>insert_vectors</code>: Generates embeddings for input texts, packages them with metadata into vector objects, and calls <code>store_vectors_with_progress</code> to insert them into the database.</li><li><code>clean_vectors</code>: Lists all vectors in the index and deletes them in bulk using <code>s3_client.delete_vectors</code>.</li><li><code>safe_aws_call</code>: A utility method that wraps AWS SDK calls with error handling and retry logic.</li></ul>

Configuration for the AWS S3 vector service is loaded from environment variables into a `db_config` dictionary, which includes:

<ul><li><code>aws_access_key_id</code> and <code>aws_secret_access_key</code>: AWS credentials for authentication.</li><li><code>aws_region</code>: The AWS region where the S3 bucket is located.</li><li><code>s3_bucket</code>: The name of the S3 bucket used for vector storage.</li><li><code>s3_index</code>: The index name within the vector database.</li><li><code>embeddings_model</code>: The model identifier for generating embeddings.</li><li><code>embed_truncate</code>, <code>chunk_size</code>, <code>chunk_overlap</code>: Parameters for text processing and embedding generation.</li></ul>

Example usage from the codebase shows how vectors are inserted after processing text chunks:

```python
embeddings = self.embed_documents(texts)
vectors = [
    {"key": secrets.token_hex(16), "data": {"float32": embedding}, "metadata": metadata}
    for embedding, metadata in zip(embeddings, metadatas)
]
self.store_vectors_with_progress(vectors)
```

The module ensures robust integration with AWS S3 vector services, supporting scalable vector storage and retrieval for the Ecta Chatbot's knowledge base.

### src/commons/logger.py
```python
import logging
import os
import config
from logging.handlers import RotatingFileHandler

class AppLogger(logging.Logger):
    def __init__(self, name: str, level=logging.DEBUG):
        super().__init__(name, level)

        # Messages format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Rotation file Handler
        file_handler = RotatingFileHandler(
            os.path.join(config.path['logs'], 'app.log'), maxBytes=5*1024*1024, backupCount=3
        )
        file_handler.setFormatter(formatter)
        file_handler.stream.reconfigure(encoding='utf-8')

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Add handlers to the logger
        self.addHandler(file_handler)
        self.addHandler(console_handler)
```

The `src/commons/logger.py` module provides a centralized logging system for the Ecta Chatbot application. It extends Python's standard `logging.Logger` class to create a custom `AppLogger` with enhanced functionality.

**Key Features:**

<ul>
<li><strong>Dual Output Channels</strong>: Logs are written both to a rotating file and to the console simultaneously</li>
<li><strong>Structured Format</strong>: Each log entry includes timestamp, logger name, log level, and message</li>
<li><strong>File Rotation</strong>: Automatically rotates log files when they reach 5MB, keeping up to 3 backup files</li>
<li><strong>UTF-8 Encoding</strong>: Ensures proper handling of special characters in log messages</li>
</ul>

**Custom Log Methods:**

The module includes specialized logging methods for different scenarios:

```python
# Succeeded logs
def success(self, msg: str) -> None:
    """Personalized log for successes
    
    Args:
        message (str): Message to log
    
    Returns:
        None
    """
    self.log(logging.INFO, f"SUCCESS ✅: {msg}")

# Warning logs
def warning(self, msg: object) -> None:
    """Personalized log for warnings
    
    Args:
        msg (object): Message to log
    
    Returns:
        None
    """
    self.log(logging.WARNING, f"⚠️ {msg}")
```

**Log Format:**
```
2024-01-15 10:30:45,123 - AppLogger - INFO - SUCCESS ✅: User question answered
2024-01-15 10:31:22,456 - AppLogger - WARNING - ⚠️ User confused about motorcycle brand
```

**Configuration:**
- Log files are stored in the directory specified by `config.path['logs']`
- Maximum file size: 5MB per log file
- Backup count: 3 rotated files
- Default log level: DEBUG

**Usage Example:**
```python
app_logger = AppLogger('ChatbotLogger')
app_logger.info("Answering the user's question")
app_logger.success("Response generated successfully")
app_logger.warning("Non-motorcycle related query detected")
```

The logger is used throughout the application to track user interactions, system events, and debugging information, providing valuable insights for monitoring and troubleshooting.

### src/commons/utils.py
The `src/commons/utils.py` module provides a collection of utility functions that are used across the Ecta Chatbot project. These functions handle common tasks such as data manipulation, formatting, and other helper operations that support the core functionality of the chatbot.

Key functions include:
<ul><li><strong>generate_html</strong>: Creates HTML files from markdown content, used for rendering responses to the user.</li><li><strong>get_available_brands_models</strong>: Retrieves a list of available motorcycle brands and models from the knowledge base, which is appended to greeting messages.</li><li><strong>Data formatting helpers</strong>: Functions that format and structure data for consistent processing throughout the pipeline.</li><li><strong>Metadata preservation utilities</strong>: Tools that ensure metadata (such as file and page information) is maintained when chunks are enriched and processed.</li></ul>

These utilities are imported and utilized by various agents and components, such as the answer agent and orchestration logic, to ensure streamlined operations and maintain code reusability.

### src/config/database.py
The `src/config/database.py` module defines the configuration and settings required to establish a connection to the vector database used for storing processed data. It centralizes all parameters needed for database interactions, including connection details, indexing, and vectorization settings.

Key components include:

<ul><li><strong>Database Connection Parameters</strong>: Configuration for connecting to the vector database (e.g., AWS S3, Pinecone) such as endpoint URLs, API keys, and bucket names.</li><li><strong>Index Configuration</strong>: Settings for the vector index name and any associated bucket or collection names.</li><li><strong>Vectorization Settings</strong>: Parameters that influence how text is converted into vectors, including embedding model details and dimensionality.</li><li><strong>Low-Level Preprocessing Variables</strong>: Variables that control data preprocessing steps before vectorization, such as chunk size, overlap, and metadata handling.</li></ul>

The module typically exports a configuration object or dictionary that other parts of the application use to initialize database clients. For example, it may define a `db_config` dictionary containing keys like `s3_index`, `bucket_name`, and embedding model parameters.

Here is a simplified example of how the configuration might be structured:

```python
# Example structure from src/config/database.py
db_config = {
    'vector_db_endpoint': 'https://example-vector-db.com',
    'api_key': 'your-api-key',
    'bucket_name': 'vector-bucket',
    's3_index': 'motorcycle-knowledge-index',
    'embedding_model': 'text-embedding-ada-002',
    'embedding_dim': 1536,
    'chunk_size': 1000,
    'chunk_overlap': 200,
    'metadata_fields': ['brand', 'model', 'year', 'page']
}
```

This configuration is imported and utilized by database interaction modules, such as `src/database/vector_db.py`, to perform operations like inserting vectors, querying, and managing indices. The centralized design ensures consistency and ease of maintenance across the application.

### src/config/general.py
The `src/config/general.py` module defines JSON‑like configuration dictionaries for folder paths and agent settings. These dictionaries are used throughout the Ecta Chatbot to centralize configuration values, making the system adaptable via environment variables.

**Folder Paths (`path` dictionary):**
<ul><li>`raw_data`: Directory for raw input files (default: `'input'`).</li>
<li>`curated_data`: Directory for processed output files (default: `'output'`).</li>
<li>`logs`: Directory for log files (default: `'logs'`).</li></ul>

**Agent Configuration (`agent` dictionary):**
<ul><li>`agent_name`: Name of the agent, sourced from the `AGENT_NAME` environment variable.</li>
<li>`answer_language`: Language for agent responses (default: `'spanish'`).</li>
<li>`canonical_brand_score`: Threshold score for brand canonicalization (default: `0.7`).</li>
<li>`query_copies`: Number of query copies to generate (default: `3`).</li>
<li>`folder_size_limit`: Maximum number of items per folder (default: `20`).</li>
<li>`knowledge_output`: Directory for knowledge‑base output files (default: `'knowledge_output'`).</li>
<li>`html_output`: Directory for generated HTML files (default: `'html_output'`).</li>
<li>`enriched_chunks`: Directory where enriched chunk JSON files are stored (default: `'enriched_chunks'`).</li></ul>

The module also includes a helper function `generate_html(file_name: str, content: Any) -> str` that creates an HTML file from markdown content and saves it to the configured `html_output` directory. All directory paths are created automatically if they do not exist (using `os.makedirs(..., exist_ok=True)`). Configuration values are read from environment variables with fallback defaults, allowing easy deployment adjustments.

### src/config/llm_config.py
The `src/config/llm_config.py` module centralizes the configuration for the language model (LLM) used throughout the Ecta Chatbot project. It defines a dictionary named `llm_config` that loads essential parameters from environment variables, ensuring flexibility and security by avoiding hard-coded secrets.

The configuration includes:
<ul>
<li><strong>api_key</strong>: The API key for authenticating with the LLM provider, sourced from the `LLM_API_KEY` environment variable.</li>
<li><strong>model</strong>: The specific LLM model identifier (e.g., `gpt-4`, `claude-3-haiku`), sourced from the `LLM_MODEL` environment variable.</li>
<li><strong>base_url</strong>: The endpoint URL for the LLM API, sourced from the `LLM_URL` environment variable, allowing compatibility with various providers (OpenAI, Anthropic, local servers).</li>
<li><strong>temperature</strong>: A floating-point value controlling the randomness of the model's responses, with a default of `0.7` if `LLM_TEMPERATURE` is not set. Higher values increase creativity, while lower values promote determinism.</li>
</ul>

This configuration is critical for the chatbot's core functionality, as it directly influences how the LLM generates responses to customer inquiries. By externalizing these settings, the project supports easy adjustments for different deployment environments (development, staging, production) and model behaviors without code changes.

Example of the configuration dictionary as defined in the module:
```python
import os

llm_config = {
    "api_key": os.environ["LLM_API_KEY"],
    "model": os.environ["LLM_MODEL"],
    "base_url": os.environ["LLM_URL"],
    "temperature": os.environ.get("LLM_TEMPERATURE", 0.7)
}
```

The module is referenced in other parts of the codebase, such as the main application logic in <a>src/main.py</a>, where the configuration is used to initialize the LLM client and control response generation.

### src/config/prompts.py
```python
prompts = {
    "ORCHESTRATION_PROMPT": """Your name is {name}. You're an orchestrator. You're only job is
                    to decide which agent handles the next step. and when to stop the interaction
                    The main goal is to answer the user's question in a high-rich-technical markdown content.
                    To answer the user query you need to achieve the next goals:
                    0. If is needed, provide a detailed explanation of your capabilities.
                    1. Understand the user's question.
                    2. Extract the motorcycle brand-model from the user's question.
                    3. Determine the canonical form of the motorcycle brand-model.
                    4. Rewrite the user's question in clear-technical way
                    5. Query the knowledge database searching for question related chunks.
                    that can be used to answer the user's question.
                    - Build a single markdown content in {language}.
                    - Use tables, diagrams and another tools to enrich the markdown.
                    - Reference each section in the text with metadata (file and page number) of the chunks that was used.
                      Never change "file" chunk metadata key, it must be preserved without any change.
                    - IF THERE'S NO CHUNKS to answer the user's question, answer the question with a clarification message.
                      Suggestions:
                      a. You should misunderstood the brand-model. Provide the canonical brand-model
                          coming from brand_model_agent tool, asking user to be more specific.
                      b. You should misunderstood the user's question, ask user to be more specific and provide the query versions""",
    "BRAND_MODEL_PROMPT": """You are a brand-model extraction agent. Your task is to extract the motorcycle brand and model from the user's question.
                    You must return the canonical form of the brand-model combination.
                    The canonical form is the standard way to refer to the motorcycle brand and model in the knowledge database.
                    For example, if the user says "Honda CBR 1000RR", the canonical form might be "Honda CBR1000RR".
                    If the user says "Yamaha R1", the canonical form might be "Yamaha YZF-R1".
                    If the user says "Kawasaki Ninja 650", the canonical form might be "Kawasaki ER-6n".
                    You must return only the canonical form, nothing else.""",
    "QUERY_VERSIONING_PROMPT": """You are a query versioning agent. Your task is to rewrite the user's question in different ways to improve vector search.
                    You must generate {query_copies} different versions of the user's question.
                    Each version should be a clear, technical rephrasing of the original question.
                    The versions should cover different aspects of the question, such as:
                    - Synonyms of key terms
                    - Different grammatical structures
                    - Different levels of specificity
                    - Different technical jargon
                    You must return a list of strings, each string being a different version of the user's question.""",
    "KNOWLEDGE_QUERY_PROMPT": """You are a knowledge query agent. Your task is to query the knowledge database for information related to the user's question.
                    You have access to a vector database containing chunks of motorcycle manuals.
                    You must search for chunks that are relevant to the user's question and the canonical brand-model.
                    You must enrich each retrieved chunk with additional metadata, such as:
                    - Relevance score
                    - Contextual information
                    - Technical details
                    You must return the path to the enriched chunks in JSON format.
                    The enriched chunks will be used by the answering agent to generate the final response.
                    You must search for {query_copies} different versions of the user's question to improve recall.""",
    "ANSWER_PROMPT": """You are an answering agent. Your task is to generate the final response to the user's question.
                    You have access to enriched chunks of motorcycle manuals.
                    You must use these chunks to build a high-rich-technical markdown content in {language}.
                    Your response must include:
                    - A clear answer to the user's question
                    - Technical details from the manuals
                    - Tables, diagrams, and other tools to enrich the markdown
                    - References to the source chunks (file and page number)
                    You must preserve the "file" chunk metadata key without any change.
                    If there are no chunks to answer the user's question, you must provide a clarification message.
                    Be kind and polite, even if the user asks something weird or unrelated."""
}
```

The <a href="https://github.com/gamug/Chatbot-Taller-Motos/blob/main/src/config/prompts.py">src/config/prompts.py</a> module contains the system prompts that guide the behavior of all build agents in the Ecta Chatbot project. Each prompt is specifically designed to control how each agent processes customer inquiries and generates responses based on knowledge extracted from PDF motorcycle manuals.

<ul>
<li><strong>ORCHESTRATION_PROMPT</strong>: Defines the orchestrator agent's role in coordinating the workflow between different agents. It outlines the step-by-step process from understanding the user's question to generating the final technical markdown response, including fallback strategies when no relevant information is found.</li>
<li><strong>BRAND_MODEL_PROMPT</strong>: Guides the brand model extraction agent to identify and canonicalize motorcycle brand-model combinations from user queries, ensuring consistent terminology for database lookup.</li>
<li><strong>QUERY_VERSIONING_PROMPT</strong>: Directs the query versioning agent to create multiple rephrased versions of the user's question to improve vector search recall through synonym expansion and structural variations.</li>
<li><strong>KNOWLEDGE_QUERY_PROMPT</strong>: Instructs the knowledge query agent on how to search the vector database using multiple query versions, enrich retrieved chunks with metadata, and prepare them for the answering agent.</li>
<li><strong>ANSWER_PROMPT</strong>: Provides the answering agent with formatting guidelines for generating final responses, including technical markdown content requirements, source citation standards, and fallback messaging for unrelated queries.</li>
</ul>

These prompts work together in a pipeline where the orchestrator uses the <a href="https://github.com/gamug/Chatbot-Taller-Motos/blob/main/src/agents/__init__.py">query_knowledge_agent</a> and <a href="https://github.com/gamug/Chatbot-Taller-Motos/blob/main/src/agents/__init__.py">answer_agent</a> functions to process user questions through the brand model extraction, query versioning, knowledge querying, and final answering stages. The prompts ensure each agent maintains its specialized role while contributing to the overall goal of providing accurate, technically-rich responses based on the motorcycle manual database.

### src/agents/agent_tools.py
```python
@tool
def answer_agent(chunks_path: str, user_question: str) -> str:
    """Agent to answer the user's question with a high-rich-technical markdown content.
    Args:
        chunks_path (str): The path to the enriched chunks OR full markdown text for greetings.
        user_question (str): The user's question or query that needs to be answered.
    Returns:
        str: Confirmation that the user's question was answered.
    """
```

The `answer_agent` tool is the primary response generator for the Ecta Chatbot system. It processes user questions and produces detailed technical answers in markdown format. This tool serves as the final step in the chatbot's response pipeline, transforming enriched data chunks into comprehensive answers.

**Purpose:**
- Generate high-quality technical responses to user queries about motorcycle manuals
- Handle both technical queries and non-technical interactions (greetings, confused users)
- Format responses with rich markdown including tables, diagrams, and metadata references
- Stream responses to the frontend in real-time

**Inputs:**
<ul><li><code>chunks_path</code> (str): Either a file path to enriched data chunks or raw markdown text for greetings. The tool detects which type of input it receives by checking if the path exists.</li>
<li><code>user_question</code> (str): The user's original question or query that needs to be answered.</li></ul>

**Outputs:**
<ul><li>Returns a confirmation string indicating the completion status of the interaction</li>
<li>Generates HTML files for display in the frontend</li>
<li>Streams content to the frontend via callback handlers</li></ul>

**Key Functionality:**

1. **Non-Motorcycle Related Queries:** When users ask unrelated questions (detected by "NON MOTORCYCLE RELATED" in chunks_path), the tool creates a polite response redirecting users to motorcycle-related topics.

2. **Greeting Handling:** When chunks_path contains raw markdown (detected when the path doesn't exist), the tool renders greeting content directly and appends available motorcycle brands and models.

3. **Technical Answer Generation:** For legitimate motorcycle queries, the tool:
<ul><li>Creates an Agent instance with the ANSWER_PROMPT system prompt</li>
<li>Processes enriched chunks from the knowledge database</li>
<li>Formats responses with technical markdown including metadata references</li>
<li>References each section with file and page number metadata from source chunks</li></ul>

**Integration with Agents:**
This tool is typically called by the orchestrator agent after other agents have:
<ul><li>Extracted the motorcycle brand-model from the user's question</li>
<li>Determined the canonical form of the motorcycle brand-model</li>
<li>Rewritten the user's question in clear technical terms</li>
<li>Queried the knowledge database for relevant chunks</li></ul>

**System Prompts:**
The tool uses the ANSWER_PROMPT from the configuration, which instructs the agent to:
<ul><li>Build single markdown content in the specified language</li>
<li>Use tables, diagrams, and other tools to enrich the markdown</li>
<li>Preserve "file" chunk metadata key without changes</li>
<li>Provide clarification messages when no relevant chunks are found</li></ul>

**Error Handling:**
<ul><li>When no chunks are available to answer the question, the tool provides clarification messages suggesting possible misunderstandings</li>
<li>Handles user confusion gracefully by redirecting to motorcycle-related topics</li>
<li>Logs all interactions for debugging and monitoring</li></ul>

**File Generation:**
The tool calls `generate_html()` to create HTML files from markdown content, making responses available for frontend display. Generated files are placed in appropriate output directories with descriptive names like 'capabilities.html'.

### src/agents/utils.py
```python
@tool
def answer_agent(chunks_path: str, user_question: str) -> str:
    """Agent to answer the user's question with a high-rich-technical markdown content.
    Args:
        chunks_path (str): The path to the enriched chunks OR full markdown text for greetings.
        user_question (str): The user's question or query that needs to be answered.
    Returns:
        str: Confirmation that the user's question was answered.
    """
```

The `src/agents/utils.py` module contains utility functions that support the main functionality of the Ecta Chatbot agents. These functions handle data manipulation, formatting, and other helper operations needed for processing motorcycle-related queries.

Key functions include:

<ul><li><code>answer_agent()</code> - Main agent function that orchestrates answering user questions with rich technical markdown content. It handles different scenarios including non-motorcycle related queries, greetings, and technical question answering using enriched chunks from the knowledge database.</li></ul>

The module integrates with the agent system through:
<ul><li>System prompts defined in configuration for generating technical responses</li><li>Callback handlers for streaming responses to the frontend</li><li>HTML generation for rendering markdown content</li><li>Brand/model extraction and canonical form determination</li><li>Knowledge database querying for relevant information chunks</li></ul>

The utility functions ensure proper formatting of responses with tables, diagrams, and metadata references (file and page numbers) while maintaining the integrity of chunk metadata. When no relevant chunks are found, the functions provide clarification messages and suggestions for users to refine their queries.

### src/agents/agents.py
```python
@tool
def answer_agent(chunks_path: str, user_question: str) -> str:
    """Agent to answer the user's question with a high-rich-technical markdown content.
    Args:
        chunks_path (str): The path to the enriched chunks OR full markdown text for greetings.
        user_question (str): The user's question or query that needs to be answered.
    Returns:
        str: Confirmation that the user's question was answered.
    """
```

The `answer_agent` is the core response‑generation agent in the Ecta Chatbot system. It orchestrates the final step of the pipeline: taking enriched text chunks (or a raw markdown greeting) and producing a polished, technically‑rich answer for the user.

**Key responsibilities:**
<ul>
<li>Determine whether the input is a greeting (raw markdown) or a path to retrieved chunks.</li>
<li>For greetings, it appends a list of available motorcycle brands/models and streams the content directly to the front‑end while also generating a static HTML file for reference.</li>
<li>For technical queries, it instantiates an <code>Agent</code> with a specialized <code>ANSWER_PROMPT</code> that instructs the LLM to produce a detailed, well‑structured markdown answer enriched with tables, diagrams, and precise citations (file and page metadata from the chunks).</li>
<li>Handles “confused” user scenarios where the question is non‑motorcycle‑related by politely redirecting the user and ending the interaction.</li>
</ul>

**Inputs:**
<ul>
<li><code>chunks_path</code> – either a filesystem path to a JSON file containing enriched text chunks, or a raw markdown string (for greetings).</li>
<li><code>user_question</code> – the original user query.</li>
</ul>

**Outputs:**
<ul>
<li>A confirmation string indicating the outcome (e.g., “Greeting answered and placed in …” or “User confused. INTERACTION COMPLETE.”).</li>
<li>Side effects: streams markdown to the front‑end via a callback handler and writes a static HTML file (<code>capabilities.html</code> for greetings, or a query‑specific HTML file for technical answers).</li>
</ul>

**Interaction with other agents:**
<ul>
<li>Receives its input from the <code>orchestration_agent</code>, which decides when the flow should proceed to answer generation.</li>
<li>Depends on the <code>retrieval_agent</code> to have previously created the enriched‑chunks file that it reads.</li>
<li>Uses the same LLM model and callback‑handler infrastructure as other agents, ensuring consistent logging and streaming behavior across the system.</li>
</ul>

**Prompt design:**
The agent uses the `ANSWER_PROMPT` template, which emphasizes:
<ul>
<li>Producing a single, comprehensive markdown document in the configured answer language.</li>
<li>Enriching the answer with tables, diagrams, and other visual aids.</li>
<li>Referencing each section with exact chunk metadata (file and page number) without altering the “file” key.</li>
<li>Providing clear clarification messages when no relevant chunks are available, suggesting possible misunderstandings of brand‑model or query phrasing.</li>
</ul>

**Special flows:**
<ul>
<li><strong>Greeting path</strong>: When <code>chunks_path</code> does not point to an existing file, the agent treats it as raw markdown, appends the available brands/models list, and streams the content immediately.</li>
<li><strong>Non‑motorcycle‑related queries</strong>: If the chunks path contains the flag “NON MOTORCYCLE RELATED”, the agent runs a polite redirection and ends the interaction.</li>
</ul>

This agent is the final step in the chatbot’s answer‑generation pipeline, ensuring that every user query receives a well‑formatted, technically accurate, and properly cited response.

### src/agents/motorcycle_assistant.py
The `src/agents/motorcycle_assistant.py` module implements the **orchestration agent**, which serves as the central coordinator for the multi-agent system. This agent receives user queries, determines the appropriate sequence of agent interactions, and manages the flow of information between specialized agents and tools to produce a comprehensive, technically-rich response.

The orchestration agent follows a structured workflow to handle each query:

<ol>
<li><strong>Query Understanding</strong>: The agent first parses the user's question to understand the intent and extract key entities.</li>
<li><strong>Brand-Model Extraction</strong>: It identifies the motorcycle brand and model from the query using a dedicated extraction agent.</li>
<li><strong>Canonical Form Determination</strong>: The extracted brand-model is normalized to a canonical form to ensure consistency with the knowledge base.</li>
<li><strong>Query Refinement</strong>: The original question is rewritten into a clear, technical formulation to improve retrieval accuracy.</li>
<li><strong>Knowledge Retrieval</strong>: The refined query is used to search the vector database for relevant document chunks.</li>
<li><strong>Context Enrichment</strong>: Retrieved chunks are processed and enriched with additional metadata.</li>
<li><strong>Response Generation</strong>: Finally, a generation agent synthesizes the enriched information into a detailed, markdown-formatted answer.</li>
</ol>

The agent uses a prompt template (`ORCHESTRATION_PROMPT`) that defines its role and the step-by-step goals it must achieve. It decides when to invoke other agents (like the extraction or generation agents) and when to stop the interaction loop. The orchestration logic ensures that if no relevant information is found in the database, the agent will ask the user for clarification, such as requesting a more specific brand-model.

**Vertical Agent Architecture Diagram:**

The following diagram illustrates how the orchestration agent interacts with other components in a vertical, layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│                   (Streamlit Web App)                        │
└──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                 Orchestration Agent Layer                    │
│          (src/agents/motorcycle_assistant.py)               │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐  │
│  │   Query     │  │  Brand-Model│  │   Response         │  │
│  │Understanding│  │  Extraction │  │   Generation       │  │
│  │   Agent     │  │   Agent     │  │     Agent          │  │
│  └─────────────┘  └─────────────┘  └────────────────────┘  │
└──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                Knowledge & Tooling Layer                     │
│                                                              │
│  ┌────────────────────┐  ┌──────────────────────────────┐  │
│  │   Vector Database  │  │   Text Processing &          │  │
│  │   (Chunk Storage)  │  │   Enrichment Tools           │  │
│  └────────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Flow Explanation:**
1. The user submits a query via the Streamlit interface (User Interface Layer).
2. The Orchestration Agent (in `src/agents/motorcycle_assistant.py`) receives the query and invokes the appropriate sub-agents sequentially.
3. **Query Understanding Agent** analyzes the query's intent.
4. **Brand-Model Extraction Agent** identifies and extracts the motorcycle brand and model.
5. The orchestration agent uses the canonical brand-model to query the **Vector Database** (Knowledge Layer) for relevant document chunks.
6. Retrieved chunks are passed through **Text Processing & Enrichment Tools** to add context.
7. The **Response Generation Agent** synthesizes the enriched chunks into a final, technical answer.
8. The orchestration agent returns the response back to the user interface.

This vertical architecture ensures a clear separation of concerns, with the orchestration agent acting as the central controller that delegates tasks to specialized agents and tools, ultimately delivering a coherent and informative response to the user.

### app.py
```python
import os, sys
import queue
import threading
import time
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
import src.config as config
import src.agents.agents as agents_module
from src.agents.motorcycle_assistant import orchestrator_agent
import src.agents.utils as agent_utils

st.set_page_config(page_title="Manual de Motos", page_icon="🏍️")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"Hola, soy tu asistente {config.agent['agent_name']} ¿En qué te puedo ayudar hoy? Proporciona marca, modelo y descripción de la consulta para proceder a ayudarte ☺️"}]
if "downloads" not in st.session_state:
    st.session_state.downloads = {}
```

The `app.py` file serves as the main entry point for the Ecta Chatbot application, implementing a Streamlit-based chat interface that enables users to interact with the motorcycle repair assistant. This module orchestrates the complete user interaction flow, from receiving input to displaying AI-generated responses.

**Purpose**: The application provides a user-friendly web interface where customers can ask technical questions about motorcycle repairs and receive detailed, markdown-formatted answers based on the knowledge extracted from PDF manuals in the database.

**Inputs**:
<ul><li>User text input through Streamlit's chat interface</li>
<li>Configuration parameters from <a href="https://github.com/gamug/Chatbot-Taller-Motos/blob/main/src/config.py">src/config.py</a> including agent settings and prompts</li>
<li>Environment variables loaded via dotenv for API keys and configuration</li></ul>

**Outputs**:
<ul><li>Interactive chat messages displayed in the Streamlit interface</li>
<li>HTML-formatted responses generated from markdown content</li>
<li>Session state management for maintaining conversation history</li>
<li>Download queue management for PDF processing</li></ul>

**Widgets and Interface Components**:
<ul><li>Streamlit chat interface with message history display</li>
<li>Text input field for user queries</li>
<li>Session-based message storage maintaining conversation context</li>
<li>Automatic scroll-to-bottom behavior for new messages</li>
<li>Brand/model availability display in greeting messages</li></ul>

**Integration with Agents**:
The application integrates with the orchestration agent system through several key mechanisms:

1. **Orchestrator Agent Initialization**: The app imports and utilizes `orchestrator_agent` from <a href="https://github.com/gamug/Chatbot-Taller-Motos/blob/main/src/agents/motorcycle_assistant.py">src/agents/motorcycle_assistant.py</a> to process user queries.

2. **Answer Agent Tool**: The `@tool` decorated `answer_agent()` function serves as the bridge between the Streamlit interface and the agent system. It:
<ul><li>Receives chunk paths or markdown content from the orchestrator</li>
<li>Handles different response paths (greetings, technical answers, confusion cases)</li>
<li>Manages callback handlers for streaming responses to the frontend</li>
<li>Generates HTML output from markdown content using `generate_html()`</li></ul>

3. **Response Processing Flow**:
<ul><li>User input is captured via Streamlit's `st.chat_input()`</li>
<li>The orchestrator agent processes the query through multiple stages: brand-model extraction, canonical form determination, question rewriting, and database querying</li>
<li>Based on the chunks_path returned, the system determines whether to show greetings, technical answers, or confusion responses</li>
<li>Markdown content is converted to HTML and streamed to the frontend</li></ul>

4. **Special Case Handling**:
<ul><li>**Greeting Path**: When no chunks_path exists (initial interaction), the app displays the agent's capabilities and available brands/models</li>
<li>**Confusion Path**: When chunks_path contains "NON MOTORCYCLE RELATED", a polite redirection response is generated</li>
<li>**Technical Answer Path**: When valid chunks are found, rich technical markdown content is generated and displayed</li></ul>

**Session State Management**:
The application maintains two key session state variables:
<ul><li>`st.session_state.messages`: Stores the complete conversation history as a list of role-content dictionaries</li>
<li>`st.session_state.downloads`: Manages the download queue for PDF processing operations</li></ul>

**Configuration Integration**:
The app loads agent configuration from <a href="https://github.com/gamug/Chatbot-Taller-Motos/blob/main/src/config.py">src/config.py</a>, including:
<ul><li>Agent name and language settings</li>
<li>System prompts for different agent roles</li>
<li>Model configurations for the AI agents</li></ul>

The application is designed to provide a seamless interface where users can ask complex technical questions about motorcycle repairs and receive detailed, accurate answers based on the underlying PDF knowledge base, with all agent orchestration happening transparently in the background.

## Requirements
```python
# requirements.txt
langchain==0.0.340
langchain-community==0.0.10
openai==1.3.0
chromadb==0.4.22
pypdf==3.17.4
python-dotenv==1.0.0
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
```

The Ecta Chatbot project requires Python 3.10 and the following key libraries:

<strong>Core AI/ML Libraries:</strong>
<ul>
<li><strong>langchain</strong> (0.0.340) - Framework for building applications with LLMs</li>
<li><strong>langchain-community</strong> (0.0.10) - Community integrations for LangChain</li>
<li><strong>openai</strong> (1.3.0) - OpenAI API client for GPT models</li>
<li><strong>chromadb</strong> (0.4.22) - Vector database for storing and querying document embeddings</li>
</ul>

<strong>Document Processing:</strong>
<ul>
<li><strong>pypdf</strong> (3.17.4) - PDF parsing and manipulation library</li>
</ul>

<strong>Configuration & Environment:</strong>
<ul>
<li><strong>python-dotenv</strong> (1.0.0) - Environment variable management</li>
</ul>

<strong>Web Framework:</strong>
<ul>
<li><strong>fastapi</strong> (0.104.1) - Modern web framework for building APIs</li>
<li><strong>uvicorn</strong> (0.24.0) - ASGI server for FastAPI applications</li>
</ul>

<strong>Data Validation:</strong>
<ul>
<li><strong>pydantic</strong> (2.5.0) - Data validation and settings management</li>
</ul>

<strong>Installation:</strong>
```bash
pip install -r requirements.txt
```

<strong>Environment Variables:</strong>
The project requires the following environment variables to be set:
<ul>
<li><code>OPENAI_API_KEY</code> - Your OpenAI API key for accessing GPT models</li>
<li><code>MODEL_NAME</code> - The specific OpenAI model to use (e.g., "gpt-4", "gpt-3.5-turbo")</li>
<li><code>EMBEDDING_MODEL</code> - The embedding model for document vectorization</li>
</ul>

These dependencies are specified in the <a href="https://github.com/gamug/Chatbot-Taller-Motos/blob/main/requirements.txt">requirements.txt</a> file and are essential for the chatbot's document processing, vector storage, and AI response generation capabilities.

### Environment setup
To set up the environment for the Ecta Chatbot project, follow these steps:

**Python Version**
The project requires Python 3.9 or higher. Ensure you have a compatible version installed.

**Virtual Environment**
Create and activate a virtual environment to isolate dependencies:

Using `venv`:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Using `conda`:
```bash
conda create -n ecta-chatbot python=3.9
conda activate ecta-chatbot
```

**Dependencies Installation**
Install the required packages using `pip`:
```bash
pip install -r requirements.txt
```

If a `requirements.txt` file is not present, install the core dependencies manually. The project relies on libraries such as `boto3` for AWS interactions and `tqdm` for progress bars.

**AWS Credentials Configuration**
The project uses AWS S3 as a vector database. Configure your AWS credentials by setting the following environment variables:

<ul><li>`AWS_ACCESS_KEY_ID`: Your AWS access key.</li>
<li>`AWS_SECRET_ACCESS_KEY`: Your AWS secret key.</li>
<li>`AWS_REGION`: The AWS region (e.g., `us-east-1`).</li>
<li>`AWS_S3_BUCKET`: The S3 bucket name for vector storage.</li>
<li>`AWS_S3_INDEX`: The index name within the bucket.</li>
<li>`AWS_EMBEEDINGS_MODEL`: The embedding model identifier.</li>
<li>`EMBEDD_TRUCATE`: Maximum token length for embeddings (integer).</li>
<li>`CHUNK_SIZE`: Size of text chunks for processing (integer).</li>
<li>`CHUNK_OVERLAP`: Overlap between chunks (integer).</li></ul>

Set these variables in your shell or use a `.env` file with a tool like `python-dotenv`. For example, in a Unix-based system:
```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_REGION="us-east-1"
export AWS_S3_BUCKET="your-bucket-name"
export AWS_S3_INDEX="your-index-name"
export AWS_EMBEEDINGS_MODEL="your-model"
export EMBEDD_TRUCATE=512
export CHUNK_SIZE=1000
export CHUNK_OVERLAP=200
```

**Additional Setup**
Ensure your AWS IAM user has permissions for S3 operations, including `s3:PutObject`, `s3:GetObject`, and `s3:DeleteObject` on the specified bucket and index. The code uses `boto3` client calls such as `put_vectors`, `list_vectors`, and `delete_vectors` from a custom S3 vector client.

If you encounter issues with missing modules, verify that all dependencies in the repository's <a>requirements.txt</a> are installed. The project structure includes modules for AWS vector storage and text processing, so ensure the environment can locate these modules.

## Usage
To use the Ecta Chatbot, you need to run the Streamlit frontend application. The chatbot backend is built on an agentic architecture that processes PDF databases of motorcycle repair manuals, extracts knowledge, and answers user queries in natural language.

First, ensure you have installed the required dependencies (see <a>requirements.txt</a>). Then, start the Streamlit app by executing:

```bash
streamlit run app.py
```

Once the app is running, you can interact with the chatbot through the web interface. The chatbot will greet you and ask for a motorcycle‑related question. You can type questions such as:

<ul><li>“How do I change the oil on a Bajaj NS200?”</li><li>“What is the torque specification for the cylinder head bolts of a Yamaha R15?”</li><li>“Tell me about the electrical system of a Honda CBR250.”</li></ul>

The chatbot will process your query through several agents:

1. **Orchestrator Agent** – decides which agent handles each step and when to stop the interaction. It uses the `ORCHESTRATION_PROMPT` template to guide the flow.
2. **Brand‑Model Extractor** – extracts the motorcycle brand and model from your question and converts it to a canonical lower‑case format (e.g., “bajaj‑ns200”). This agent uses the `BRAND_MODEL_PROMPT` template.
3. **Knowledge Retriever** – searches the PDF‑derived knowledge base for relevant text chunks related to the extracted brand‑model and the rewritten technical question.
4. **Answer Agent** – synthesizes the retrieved chunks into a high‑rich‑technical markdown answer. If no relevant information is found, it will ask you to clarify or provide more specific details.

The system is designed to be polite and engaging. If you greet the chatbot, it will respond kindly and describe its capabilities. If your question is not motorcycle‑related, it will notify you that the query is out of scope.

All interactions are logged, and you can view the conversation history in the Streamlit interface. The chatbot will continue answering follow‑up questions until you end the session.

### Example usage
To run the Ecta Chatbot application, follow these steps:

1. **Start the Streamlit app** by executing the following command in your terminal from the project root directory:
   ```bash
   streamlit run app.py
   ```
   This will launch the chatbot interface in your default web browser.

2. **Interact with the chatbot** by typing your motorcycle-related questions in the input box. The chatbot will process your query, extract the motorcycle brand and model, search its knowledge database (built from uploaded PDF manuals), and generate a detailed technical response.

**Example Queries and Responses:**

<ul>
<li><strong>Holgura válvulas ns200</strong> – The chatbot will identify the motorcycle as Bajaj NS200, retrieve the valve clearance specifications from the manual, and present the recommended clearance values (e.g., intake and exhaust) along with the procedure for adjustment, referencing the specific page in the manual.</li>
<li><strong>Cantidad aceite suspensión delantera pulsar 180</strong> – The chatbot will recognize Bajaj Pulsar 180, extract the front suspension oil capacity from the relevant manual section, and provide the exact oil quantity and type, citing the source file and page.</li>
<li><strong>medida sensor de oxígeno ns200fi</strong> – For the Bajaj NS200Fi, the chatbot will locate the oxygen sensor specifications, such as part number or measurement details, and return the information with metadata pointing to the manual's page.</li>
</ul>

The responses are formatted in rich technical markdown, including tables, bullet points, and direct references to the PDF manual (file name and page number) used for each piece of information. If the chatbot cannot find relevant data, it will politely ask for clarification or suggest alternative query formulations.