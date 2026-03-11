import os

db_config = {
    "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
    "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
    "aws_region": os.environ["AWS_REGION"],
    "s3_bucket": os.environ["AWS_S3_BUCKET"],
    "s3_index": os.environ["AWS_S3_INDEX"],
    "embeddings_model": os.environ["AWS_EMBEEDINGS_MODEL"],
    "file_source": "manuales_motos",
    "embed_truncate": int(os.environ["EMBEDD_TRUCATE"]),
    "chunk_size": int(os.environ["CHUNK_SIZE"]),
    "chunk_overlap": int(os.environ["CHUNK_OVERLAP"])
}