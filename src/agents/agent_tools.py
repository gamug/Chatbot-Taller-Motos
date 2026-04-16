import asyncio, difflib, json, httpx, markdown, os, secrets, shutil
from strands.models.openai import OpenAIModel
from bs4 import BeautifulSoup
from strands import Agent, tool
import pandas as pd

import config
from src import app_logger
from src.commons import AWSClient, get_brands

brands = get_brands()
aws_client = AWSClient()
model = OpenAIModel(
    model_id=config.llm_config['model'],
    client_args={
        "api_key": config.llm_config['api_key'],
        "base_url": config.llm_config['base_url']
    }
)

@tool
async def file_write(path: str, content: str) -> str:
    """Write content to a file without confirmation.
        This tool can be used in parallel with the generate_html tool.
    
    Args:
        path (str): The path to the file.
        content (str): The content to write to the file.
    Returns:
        str: file_path where the file was created.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: open(path, "w", encoding="utf-8").write(content)
    )
    return path

@tool
def folder_integrity(folder_path: str) -> None:
    """Prevents the folder to increase in size without control.
    Args:
        folder_path (str): The folder path to check.
    Returns:
        None: Erase the folder in case of high folder size.
        create the folder in case it doesn't exist.
    """
    app_logger.info("Checking folder integrity")
    if os.path.exists(folder_path) and\
        len(os.listdir(folder_path))>config.agent['folder_size_limit']:
            shutil.rmtree(folder_path)
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
    app_logger.info("Folder integrity checked")

@tool
async def canonical_brand_models(brand_model: str) -> dict:
    """Given an identified tentative brand and model, returns the best fit of possible brands
    and models with a similarity score.
    This tool must be used in parallel many times (if possible) to increase performance.
    Args:
        brand_model (str): The identified tentative brand and model in "brand-model" lower case
        format, e.g. "bajaj-ns200". All the letters in the provided brand-model must be lowercase.
    Returns:
        dict: The best fit of possible canonical brand and model combinations with a
        similarity score in json format.
        e.g.
        {
            "brand-model": "bajaj-ns200",
            "score": 0.8
        }
    """
    app_logger.info("Trying to find the best fit of possible canonical brand-model combinations")
    
    loop = asyncio.get_event_loop()

    def compute():
        motorcycles = [dict_['motorcycle'] for dict_ in brands.values()]
        df = pd.DataFrame(
            {
                'brand-model': motorcycles,
                'score': [difflib.SequenceMatcher(None, brand_model, moto).ratio() for moto in motorcycles]
            }
        ).sort_values(by='score', ascending=False).head(1)
        response = df.to_dict('records')[0]
        app_logger.info(f"Best fit: {response}")
        return response

    return await loop.run_in_executor(None, compute)

@tool
def web_search(query: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    r = httpx.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers=headers
    )
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for result in soup.select(".result__body")[:5]:
        title = result.select_one(".result__title")
        snippet = result.select_one(".result__snippet")
        if title and snippet:
            results.append(f"{title.get_text()}: {snippet.get_text()}")
    return "\n".join(results)

@tool
async def query_knowledge_async(queries: list[str], canonical_brand_model: str) -> str:
    """Querying the knowledge database searching for question related chunks.
        This tool uses query_db asynchronously in all queries to increase performance.
        Then it uses enrich_one in parallel to enrich the chunks with confident data.
    Args:
        queries (list[str]): The rewritten query versions in a list.
        canonical_brand_model (str): The best fit of possible canonical brand and model combinations.
    Returns:
        str: path to the enriched chunks in json format.
    """
    app_logger.info("Querying knowledge database searching for question related chunks")
    brand = canonical_brand_model.split('-')[0]
    mod = '-'.join(canonical_brand_model.split('-')[1:])
    filtering = {"$and": [{"brand": {"$eq": brand}}, {"model": {"$eq": mod}}]}

    # retrieve chunks in parallel
    chunks = await aws_client.query_db_async(queries, filtering)
    app_logger.info(f"Found {len(chunks)} chunks in knowledge database")

    # assign priority based on position (duplication count already sorted desc)
    def get_priority(i: int) -> str:
        if i < len(chunks) // 3:
            return "high"
        elif i < 2 * len(chunks) // 3:
            return "medium"
        return "low"

    # enrich all chunks in parallel
    loop = asyncio.get_event_loop()

    async def enrich_one(chunk: dict, priority: str) -> str:
        def run_agent():
            agent = Agent(
                model=model,
                system_prompt=config.prompts['ENRICHMENT_PROMPT']
            )
            return str(agent(
                f"Enrich the chunk with confident data you can provide "
                f"(don't hallucinate, the data added must be 100% confident). "
                f"The chunk is '{chunk}'. The priority is '{priority}'"
            ))
        return await loop.run_in_executor(None, run_agent)

    enriched_chunks = await asyncio.gather(*[
        enrich_one(chunk, get_priority(i))
        for i, chunk in enumerate(chunks)
    ])
    os.makedirs(config.agent['enriched_chunks'], exist_ok=True)
    path = os.path.join(config.agent['enriched_chunks'], f'{secrets.token_hex(4)}.json')
    with open(path, 'w') as f:
        json.dump(enriched_chunks, f)
    app_logger.info(f"Enriched {len(enriched_chunks)} chunks")
    return path