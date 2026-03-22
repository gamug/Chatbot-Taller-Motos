import difflib, json, cv2, os, re
import numpy as np, pandas as pd
from typing import List

from strands.models.openai import OpenAIModel
from strands import Agent
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config

model = OpenAIModel(
    model_id=os.environ['LLM_MODEL'],  # or "deepseek-reasoner" for R1
    client_args={
        "api_key": os.environ["LLM_API_KEY"],
        "base_url": os.environ["LLM_URL"]
    }
)
agent = Agent(model=model, tools=[])

def check_directories():
    """Ensure that all configured directories exist on the filesystem.

    This function iterates over the directory paths defined in the configuration
    and creates any that do not already exist.

    Args:
        None

    Returns:
        None
    """
    for dir in config.path.values():
        os.makedirs(dir, exist_ok=True)

def map_files(path: str, file_list: list[str]):
    """Recursively map files in a directory and its subdirectories. This function
    is used to generate a list of file paths in a directory and its subdirectories.

    Args:
        path (str): The path to the directory to map.
        file_list (list[str]): A list to store the mapped file paths.

    Returns:
        None
    """
    files = os.listdir(path)
    for file in files:
        if os.path.isdir(os.path.join(path, file)):
            map_files(os.path.join(path, file), file_list)
        else:
            file_list.append(os.path.join(path, file))

def extract_moto_models(query:str, brands: dict[str, dict]) -> List[dict]:
    """Extracts motorcycle models from a query using an LLM.
    Args:
        query (str): The query to extract models from.
        brands (dict[str, dict]): A dictionary of motorcycle brands and their models.
    Returns:
        A list of motorcycle models extracted from the query."""
    result = agent(config.prompts['moto_models_prompt'].format(query=query))
    result = json.loads(result)
    if not result['brand'] or not result['model']:
        return []
    motorcycle = f"{result['brand'].lower()}-{result['model'].lower()}"
    motorcycles = [dict_['motorcycle'] for dict_ in brands.values()]
    matches_ratio = [difflib.SequenceMatcher(None, motorcycle, dict_['motorcycle']).ratio() for dict_ in brands.values()]
    df = pd.DataFrame({'brand': motorcycles, 'score': matches_ratio})
    return df.sort_values(by='score', ascending=False).reset_index(drop=True).head(5).to_dict('records')

def extract_brand_from_file_source() -> dict[str, dict[str, str]]:
    """Extracts brand and model information from the file names in the raw data folder.

    Args:
        None

    Returns:
        dict[str, dict[str, str]]: A dictionary of brand and model information.
    """
    files = []
    map_files(config.path['raw_data'], files)
    brand_extraction = {}
    brands = [file.split('\\')[1] for file in files]
    manuals = [file.split('\\')[-1].split('.')[0] for file in files]
    for i, manual in enumerate(manuals):
        string = manual
        for patt in config.brand_regexes:
            string = re.sub(patt, '', string, flags=re.IGNORECASE)
        string = re.sub(brands[i], '', re.sub(' {2,}', ' ', string, flags=re.IGNORECASE)).strip()
        model = None if string in [manual.split('.')[0], ''] else string.lower()
        brand_extraction[manual] = {
            'manual': manual,
            'motorcycle': f'{brands[i].strip().lower()}-{model}' if model else brands[i].strip().lower(),
            'brand': brands[i].strip().lower(),
            'model': model
        }
    return brand_extraction

def get_brands() -> dict[str, dict[str, str]]:
    """Gets the brands from the raw data folder.
    Uses regex to extract the brand and model from the file name. And saves it
    in a dictionary so the agent can have it as single source of truth in
    brand-model extraction.

    Args:
        None

    Returns:
        list[dict[str, str]]: List of brands
    """
    if not os.path.exists('brand.json'):
        brand_extraction = extract_brand_from_file_source()
        with open('brand.json', 'w') as f:
            json.dump(brand_extraction, f, indent=4)
    else:
        with open('brand.json', 'r') as f:
            brand_extraction = json.load(f)
    return brand_extraction

def get_output_path(base_path: str, file: str) -> str:
    """Get the output path for a file. This is used in data processing scripts.

    Args:
        base_path (str): The base path of the file.
        file (str): The name of the file.

    Returns:
        str: The output path for the file.
    """
    end = base_path.split(config.path['raw_data']+'\\')[-1]
    output_path = os.path.join(config.path['curated_data'], end)
    return os.path.join(output_path, f"{file.split('.')[0]}.json")

def get_nlp_tools() -> RecursiveCharacterTextSplitter:
    """Function used un data processing to get the splitter for the text.

    Args:
        None

    Returns:
        RecursiveCharacterTextSplitter: The splitter for the text.
    """
    #Creating text splitter
    return RecursiveCharacterTextSplitter(
        chunk_size=config.db_config['chunk_size'],
        chunk_overlap=config.db_config['chunk_overlap']
    )

def process_image(image) -> np.array:
    # converting bytes → NumPy array
    image = np.frombuffer(image, np.uint8)

    # encoding the image with OpenCV
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)

    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 2
    )