import os

db_config = {
    "mongo_database": os.environ["MONGO_DATABASE"],
    "mongo_user": os.environ["MONGO_USER"],
    "mongo_pass": os.environ["MONGO_PASS"],
    "mongo_uri":  os.environ["MONGO_URI"],
    "file_source": "manuales_motos",
    "embedd_task": os.environ["EMBEDD_TASK"],
    "embedd_truncate": os.environ["EMBEDD_TRUCATE"],
    "chunk_size": os.environ["CHUNK_SIZE"],
    "chunk_overlap": os.environ["CHUNK_OVERLAP"]
}