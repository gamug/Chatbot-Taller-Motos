import json, os, sys

from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.path.join(os.getcwd(), 'src'))

import src.config as config
from src.data_processing.pdf_processing import process_database, process_pdf_images

base_path, errors = config.path['raw_data'], {}
print('processing text pdf...')
process_database(base_path, errors)
# print(errors)
print('processing image pdf...')
errors_image = process_pdf_images(errors)

with open(os.path.join(config.path['logs'], 'data_processing_errors.json'), 'w') as f:
    json.dump(errors_image, f, indent=4, default=str)