import boto3, json, math, random, secrets, time
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

import config

from langchain_openai import ChatOpenAI


def get_llm():
    return ChatOpenAI(
            api_key=config.llm_config["api_key"],
            model=config.llm_config["model"],
            base_url=config.llm_config["base_url"],
            temperature=config.llm_config["temperature"]
        )


class AWSClient:
    def __init__(self):
        self.bucket_name = config.db_config['s3_bucket']
        self.s3_client = boto3.client(
            's3vectors',
            aws_access_key_id=config.db_config['aws_access_key_id'],
            aws_secret_access_key=config.db_config['aws_secret_access_key'],
            region_name=config.db_config['aws_region']
        )
        self.bedrock_client = boto3.client("bedrock-runtime", region_name=config.db_config['aws_region'])

    def embed_documents(self, documents: list[str], max_workers: int = 6):

        def embed_single(text: str, retries=6):

            body = json.dumps({
                "inputText": text,
                "dimensions": config.db_config['embed_truncate'],
                "normalize": True
            })

            for attempt in range(retries):

                try:

                    response = self.bedrock_client.invoke_model(
                        modelId=config.db_config["embeddings_model"],
                        body=body,
                        contentType="application/json",
                        accept="application/json"
                    )

                    result = json.loads(response["body"].read())
                    return result["embedding"]

                except ClientError as e:

                    if e.response["Error"]["Code"] == "ThrottlingException":

                        # exponential backoff + jitter
                        sleep_time = (2 ** attempt) + random.uniform(0, 1)
                        time.sleep(sleep_time)

                    else:
                        raise

            raise RuntimeError("Max retries exceeded for embedding request")

        embeddings = [None] * len(documents)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            futures = {
                executor.submit(embed_single, doc): i
                for i, doc in enumerate(documents)
            }

            for future in tqdm(as_completed(futures),
                            total=len(futures),
                            desc="Generating embeddings",
                            unit="chunk",
                            leave=False
                            ):

                idx = futures[future]
                embeddings[idx] = future.result()

        return embeddings

    def store_vectors_with_progress(self, vectors, batch_size=100):
        total_batches = math.ceil(len(vectors) / batch_size)

        with tqdm(total=total_batches, desc="Uploading vectors", unit="batch", leave=False) as pbar:
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i+batch_size]
                self.s3_client.put_vectors(
                    vectorBucketName=self.bucket_name,
                    indexName=config.db_config['s3_index'],
                    vectors=batch
                )
                pbar.update(1)

        print(f"{len(vectors)} vectors placed in the index {config.db_config['s3_index']}.")
    
    def insert_vectors(self, texts: list[str], metadatas: list[dict]):
        embeddings = self.embed_documents(texts)
        vectors = [
            {"key": secrets.token_hex(16), "data": {"float32": embedding}, "metadata": metadata}
            for embedding, metadata in zip(embeddings, metadatas)
        ]
        self.store_vectors_with_progress(vectors)
    
    def clean_vectors(self):
        response = self.s3_client.list_vectors(
            vectorBucketName=self.bucket_name,
            indexName=config.db_config['s3_index']
        )
        ids = [v["key"] for v in response["vectors"]]
        if len(ids):
            self.s3_client.delete_vectors(
                vectorBucketName=self.bucket_name,
                indexName=config.db_config['s3_index'],
                keys=ids
            )
            
    def query_db(self, query: str, filtering: dict[str, str], top_k: int = 5) -> list[dict]:
        request = json.dumps({
            "inputText": query,
            "dimensions": config.db_config['embed_truncate'],
            "normalize": True
        })

        # Invoke the model with the request and the model ID, e.g., Titan Text Embeddings V2. 
        response = self.bedrock_client.invoke_model(modelId="amazon.titan-embed-text-v2:0", body=request)

        # Decode the model's native response body.
        body = response["body"].read()
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        model_response = json.loads(body)
        embedding = model_response["embedding"]
        # Performa a similarity query
        query = self.s3_client.query_vectors(
            vectorBucketName=config.db_config['s3_bucket'],
            indexName=config.db_config['s3_index'],
            queryVector={"float32":embedding},
            topK=top_k, 
            filter=filtering,
            returnDistance=True,
            returnMetadata=True
        )
        query = [result['metadata']['text'] for result in query['vectors']]
        return '\n'.join(query)