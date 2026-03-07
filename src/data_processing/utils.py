import config, cv2, os, torch
import numpy as np
from huggingface_hub import login
login(os.environ['HF_TOKEN'])

from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

def get_output_path(base_path: str, file: str) -> str:
    start = base_path.split('\\input\\')[0]
    end = base_path.split('\\input\\')[-1]
    output_path = os.path.join(start, 'output', end)
    return os.path.join(output_path, f"{file.split('.')[0]}.parquet")

def get_nlp_tools() -> tuple[RecursiveCharacterTextSplitter, SentenceTransformer]:
    #loading embeddings model
    # Check if CUDA is available
    device = "cuda" if torch.cuda.is_available() else "cpu"

    embeddings = SentenceTransformer("google/embeddinggemma-300m", device=device)
    #Creating text splitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=int(config.db_config['chunk_size']),
        chunk_overlap=int(config.db_config['chunk_overlap'])
    )
    return splitter, embeddings

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