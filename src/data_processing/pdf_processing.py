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

def process_database(base_path: str, errors: dict[str, str], brands: Any = None) -> None:
    """Processes a single file or folder of files.

    Args:
        base_path (str): The path to the file or folder to process.
        errors (dict): A dictionary to store errors.
        brands (dict[dict[str, str]], optional): The relation between file and brand-model.
    returns:
        None
    """
    folder = os.path.dirname(base_path)
    file = os.path.basename(base_path)
    output_path = get_output_path(folder, file)
    if os.path.isdir(base_path):
        for element in os.listdir(base_path):
            process_database(os.path.join(base_path, element), errors, brands)
    elif not os.path.exists(output_path):
        try:
            print(f'\tprocessing file {file}')
            doc = fitz.open(base_path)
            text = [page.get_text() for page in doc]
            process_pdf(text, folder, file, brands)
        except Exception as e:
            errors[base_path] = str(e)
    
def get_pdf_images(file: str) -> list:
    """Extracts images from a pdf file that does not contain text.

    Args:
        file (str): The path to the pdf file.

    Returns:
        list: A list of images extracted from the pdf file."""
    doc = fitz.open(file)

    pdf_images = []
    # Iterate along the pages
    for page_index in range(len(doc)):
        page = doc[page_index]
        # Get images from the page
        images = page.get_images(full=True)
        
        for img in images:
            xref = img[0]  # Internal image reference
            base_image = doc.extract_image(xref)
            pdf_images.append(process_image(base_image["image"]))
    return pdf_images

def process_pdf_images(errors: dict[str, str]) -> dict[str, str]:
    """Processes a single file or folder of files to extract content from images.

    Args:
        base_path (str): The path to the file or folder to process.
        errors (dict): A dictionary with previous PDF not processed due to abcense
        of text.

    Returns:
        dict: A dictionary with the errors."""
    errors_image = {}
    brands = get_brands()
    for base_path in errors:
        folder = os.path.dirname(base_path)
        file = os.path.basename(base_path)
        output_path = get_output_path(folder, file)
        if not os.path.exists(output_path):
            try:
                print(f'\tprocessing {file}')
                pdf_images = get_pdf_images(base_path)
                text = [pytesseract.image_to_string(img, lang='"spa+eng') for img in pdf_images]
                process_pdf(text, base_path, file, brands=brands)
            except Exception as e:
                errors_image[folder] = str(e)
    return errors_image