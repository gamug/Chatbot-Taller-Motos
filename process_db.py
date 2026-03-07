import os, sys

from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.path.join(os.getcwd(), 'src'))

import src.config as config
from src.data_processing.pdf_processing import process_database, process_pdf_images

base_path, errors = config.path['raw_data'], {}
print('processing text pdf...')
process_database(base_path, errors)
print('processing image pdf...')
process_pdf_images(errors)