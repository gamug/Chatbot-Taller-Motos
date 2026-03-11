import fitz, json, os, pytesseract, re

from commons.utils import get_output_path, get_nlp_tools, process_image
from tools.tools import extract_moto_models
from commons import AWSClient

pytesseract.pytesseract.tesseract_cmd = os.environ['TESSERACT_PATH']

splitter, aws_client = get_nlp_tools(), AWSClient()

def process_pdf(text: list[str], base_path: str, file: str) -> None:
    metadatas = [re.sub('(\n* *\n)+', '\n', page) for page in text]
    metadatas = [re.sub(' +', ' ', page).strip().lower() for page in metadatas]
    metadatas = [[re.sub('\n', ' ', chunk) for chunk in splitter.split_text(page) if len(chunk)>20] for page in metadatas]
    brand_model = {}
    for _ in range(5):
        brand_model = extract_moto_models(file)
        if brand_model:
            del brand_model["query"]
            del brand_model["text"]
            break
    if not brand_model:
        brand_model = {'model': 'no model', 'brand': 'no brand'}
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

def process_database(base_path: str, errors: dict):
    folder = os.path.dirname(base_path)
    file = os.path.basename(base_path)
    output_path = get_output_path(folder, file)
    if os.path.isdir(base_path):
        for element in os.listdir(base_path):
            process_database(os.path.join(base_path, element), errors)
    elif not os.path.exists(output_path):
        try:
            print(f'\tprocessing file {file}')
            doc = fitz.open(base_path)
            text = [page.get_text() for page in doc]
            process_pdf(text, folder, file)
        except Exception as e:
            errors[base_path] = str(e)
    
def get_pdf_images(file: str) -> list:
    doc = fitz.open(file)

    pdf_images = []
    # Iterar por las páginas
    for page_index in range(len(doc)):
        page = doc[page_index]
        # Obtener las imágenes de la página
        images = page.get_images(full=True)
        
        for img in images:
            xref = img[0]  # referencia interna de la imagen
            base_image = doc.extract_image(xref)
            pdf_images.append(process_image(base_image["image"]))
    return pdf_images

def process_pdf_images(errors: dict[str, str]) -> dict[str, str]:
    errors_image = {}
    for base_path in errors:
        folder = os.path.dirname(base_path)
        file = os.path.basename(base_path)
        output_path = get_output_path(folder, file)
        if not os.path.exists(output_path):
            try:
                print(f'\tprocessing {file}')
                pdf_images = get_pdf_images(base_path)
                text = [pytesseract.image_to_string(img, lang='"spa+eng') for img in pdf_images]
                process_pdf(text, base_path, file)
            except Exception as e:
                errors_image[folder] = str(e)
    return errors_image