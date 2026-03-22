import difflib, httpx, markdown, os, pdfkit, shutil
from bs4 import BeautifulSoup
from strands import tool
import pandas as pd

import config
from src import app_logger
from src.commons import AWSClient, get_brands

brands = get_brands()
aws_client = AWSClient()



_download_q = None  # will be set before each agent call

@tool
def generate_pdf(filename: str) -> str:
    """Generate a PDF from markdown content and make it available for download.
    Args:
        filename (str): The filename of the markdown file.
    Returns:
        str: The path to the generated PDF file.
    """
    os.makedirs(config.agent['knowledge_output'], exist_ok=True)
    output_path = os.path.join(config.agent['pdf_output'], f'{os.path.basename(filename).split(".")[0]}.pdf')
    with open(os.path.join(config.agent['knowledge_output'], filename), "r", encoding="utf-8") as f:
        html = markdown.markdown(f.read(), extensions=["tables", "fenced_code"])
    pdfkit.from_string(html, output_path)

    if _download_q:
        _download_q.put(output_path)

    return f"PDF generated at {output_path}"

@tool
def file_write(path: str, content: str) -> str:
    """Write content to a file without confirmation."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"File {path} written successfully"

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
def canonical_brand_models(brand_model:str) -> dict:
    """Given an identified tentative brand and model, returns the best fit of possible brands
    and models with a similarity score.
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
    motorcycles = [dict_['motorcycle'] for dict_ in brands.values()]
    df = pd.DataFrame(
        {
            'brand-model': motorcycles,
            'score': [difflib.SequenceMatcher(None, brand_model, moto).ratio() for moto in motorcycles]
        }
    ).sort_values(by='score', ascending=False).head(1)
    response = df.to_dict('records')[0]
    app_logger.info(f"Best fit of possible canonical brand-model combinations: {response}")
    return response

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
def query_knowledge(queries: list[str], canonical_brand_model: str) -> list[str]:
    """Quering the knowledge database searching for question related chunks.
    Args:
        queries (list[str]): The rewritten query versions in a list.
        canonical_brand_model (str): The best fit of possible canonical brand and model combinations.
    Returns:
        list[str]: The relevant context retrieved from the knowledge base that can be used to answer the user's question.
    """
    app_logger.info("Quering knowledge database searching for question related chunks")
    chunks = []
    brand, model = canonical_brand_model.split('-')
    filtering = {"$and": [{"brand": {"$eq": brand}}, {"model": {"$eq": model}}]}
    for query in queries:
        chunks.extend(aws_client.query_db(
            query,
            filtering
        ))
    app_logger.info(f"Found {len(chunks)} chunks in knowledge database")
    return chunks