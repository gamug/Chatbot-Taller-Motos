import fitz, os, pytesseract, re
import pandas as pd

from .utils import get_output_path, get_nlp_tools, process_image

pytesseract.pytesseract.tesseract_cmd = os.environ['TESSERACT_PATH']
splitter, embeddings = get_nlp_tools()

def process_pdf(text: list[str], base_path: str, file: str) -> None:
    text = [re.sub('(\n* *\n)+', '\n', page) for page in text]
    text = [re.sub(' +', ' ', page).strip().lower() for page in text]
    text = [[re.sub('\n', ' ', chunk) for chunk in splitter.split_text(page)] for page in text]
    text = [pd.DataFrame({
            'text': page,
            'page': [i+1 for _ in range(len(page))],
            'chunk': range(1, len(page)+1)
        }) for i, page in enumerate(text) if len(page)]
    text = pd.concat(text).reset_index(drop=True).assign(file=file)
    text["embedding"] = [emb.tolist() for emb in embeddings.encode(text.text.tolist())]
    output_path = get_output_path(base_path, file)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    text.to_parquet(output_path)

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
            doc = fitz.open(os.path.join(base_path, file))
            text = [page.get_text() for page in doc]
            process_pdf(folder, file, text)
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