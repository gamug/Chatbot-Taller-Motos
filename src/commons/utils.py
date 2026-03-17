import config, cv2, os, re
import numpy as np

from langchain_text_splitters import RecursiveCharacterTextSplitter

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
    files = os.listdir(path)
    for file in files:
        if os.path.isdir(os.path.join(path, file)):
            map_files(os.path.join(path, file), file_list)
        else:
            file_list.append(os.path.join(path, file))

def get_brands() -> list[dict[str, str]]:
    """Gets the brands from the raw data folder.
    Uses regex to extract the brand and model from the file name.

    Returns:
        list[dict[str, str]]: List of brands
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

def get_output_path(base_path: str, file: str) -> str:
    end = base_path.split(config.path['raw_data']+'\\')[-1]
    output_path = os.path.join(config.path['curated_data'], end)
    return os.path.join(output_path, f"{file.split('.')[0]}.json")

def get_nlp_tools() -> RecursiveCharacterTextSplitter:
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