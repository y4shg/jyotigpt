from jyotigpt.config import VECTOR_DB

if VECTOR_DB == "milvus":
    from jyotigpt.retrieval.vector.dbs.milvus import MilvusClient

    VECTOR_DB_CLIENT = MilvusClient()
elif VECTOR_DB == "qdrant":
    from jyotigpt.retrieval.vector.dbs.qdrant import QdrantClient

    VECTOR_DB_CLIENT = QdrantClient()
elif VECTOR_DB == "opensearch":
    from jyotigpt.retrieval.vector.dbs.opensearch import OpenSearchClient

    VECTOR_DB_CLIENT = OpenSearchClient()
elif VECTOR_DB == "pgvector":
    from jyotigpt.retrieval.vector.dbs.pgvector import PgvectorClient

    VECTOR_DB_CLIENT = PgvectorClient()
elif VECTOR_DB == "elasticsearch":
    from jyotigpt.retrieval.vector.dbs.elasticsearch import ElasticsearchClient

    VECTOR_DB_CLIENT = ElasticsearchClient()
else:
    from jyotigpt.retrieval.vector.dbs.chroma import ChromaClient

    VECTOR_DB_CLIENT = ChromaClient()
