import config, cv2, os
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