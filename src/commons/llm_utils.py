import boto3, json, math, secrets, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from tqdm import tqdm

import config


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

    def safe_aws_call(self, func, retries=5, **kwargs) -> Any:
        """Retry AWS calls in case of throttling.

        Args:
            func: The function to call.
            retries: The number of retries.
            **kwargs: The arguments to pass to the function.

        Returns:
            The result of the function.
        """
        for i in range(retries):
            try:
                return func(**kwargs)
            except Exception as e:
                if "ThrottlingException" in str(e):
                    time.sleep(2 ** i)  # exponential backoff
                else:
                    raise e
        raise Exception("Max retries exceeded")

    def embed_documents(self, documents: list[str], max_workers: int = 6) -> list[list[float]]:
        """Generate embeddings for a list of documents. Uses Bedrock to generate embeddings
        and multiple threads to speed up the process.

        Args:
            documents (list[str]): The documents to embed.
            max_workers (int, optional): The maximum number of workers to use. Defaults to 6.

        Returns:
            list: A list of embeddings.
        """
        def embed_single(text: str) -> list[float]:
            """Generate embeddings for a single document.

            Args:
                text (str): The document to embed.

            Returns:
                list[float]: The embeddings.
            """
            body = json.dumps({
                "inputText": text,
                "dimensions": config.db_config['embed_truncate'],
                "normalize": True
            })
            response = self.safe_aws_call(
                self.bedrock_client.invoke_model,
                modelId=config.db_config["embeddings_model"],
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            return json.loads(response["body"].read())

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

    def store_vectors_with_progress(self, vectors, batch_size=100) -> None:
        """Store vectors in S3 with progress bar.

        Args:
            vectors (list): A list of vectors to store.
            batch_size (int, optional): The batch size to use. Defaults to 100.
        
        Returns:
            None
        """
        total_batches = math.ceil(len(vectors) / batch_size)

        with tqdm(total=total_batches, desc="Uploading vectors", unit="batch", leave=False) as pbar:
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i+batch_size]
                self.safe_aws_call(
                    self.s3_client.put_vectors,
                    vectorBucketName=self.bucket_name,
                    indexName=config.db_config['s3_index'],
                    vectors=batch
                )
                pbar.update(1)

        print(f"{len(vectors)} vectors placed in the index {config.db_config['s3_index']}.")
    
    def insert_vectors(self, texts: list[str], metadatas: list[dict]) -> None:
        """Insert vectors into the database.

        Args:
            texts (list[str]): A list of text chunks.
            metadatas (list[dict]): A list of metadata for each text chunk.

        Returns:
            None
        """
        embeddings = self.embed_documents(texts)
        vectors = [
            {"key": secrets.token_hex(16), "data": {"float32": embedding}, "metadata": metadata}
            for embedding, metadata in zip(embeddings, metadatas)
        ]
        self.store_vectors_with_progress(vectors)
    
    def clean_vectors(self) -> None:
        """Delete all vectors from the database."""
        response = self.safe_aws_call(
            self.s3_client.list_vectors,
            vectorBucketName=self.bucket_name,
            indexName=config.db_config['s3_index']
        )
        ids = [v["key"] for v in response["vectors"]]
        if len(ids):
            self.safe_aws_call(
                self.s3_client.delete_vectors,
                vectorBucketName=self.bucket_name,
                indexName=config.db_config['s3_index'],
                keys=ids
            )

    def retrieve_embedding(self, query: str) -> list[float]:
        """Get a single embedding from the bedrock service

        Args:
            query (str): The query to embed.

        Returns:
            list[float]: The embedding.
        """
        request = json.dumps({
            "inputText": query,
            "dimensions": config.db_config['embed_truncate'],
            "normalize": True
        })

        # Invoke the model with the request and the model ID, e.g., Titan Text Embeddings V2.
        response = self.safe_aws_call(
            self.bedrock_client.invoke_model,
            modelId="amazon.titan-embed-text-v2:0",
            body=request
        )

        # Decode the model's native response body.
        body = response["body"].read()
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        model_response = json.loads(body)
        return model_response["embedding"]

    def query_db(
        self,
        query: str,
        filtering: dict[str, list[dict[str, dict[str, str]]]],
        top_k: int = 3) -> list[dict[str, str]]:
        """Query the database searching for question related chunks.

        Args:
            query (str): The query to search for.
            filtering (dict[str, list[dict[str, dict[str, str]]]]): The metadata filter to apply in database.
            top_k (int, optional): The number of results to return. Defaults to 3.

        Returns:
            list[str]: A list of text chunks.
        """
        embedding = self.retrieve_embedding(query)
        # Perform a similarity query
        query = self.safe_aws_call(
            self.s3_client.query_vectors,
            vectorBucketName=config.db_config['s3_bucket'],
            indexName=config.db_config['s3_index'],
            queryVector={"float32":embedding},
            topK=top_k, 
            filter=filtering,
            returnDistance=True,
            returnMetadata=True
        )
        return [result['metadata'] for result in query['vectors']]