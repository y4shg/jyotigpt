"""pgvector vector-store client.

Either reuses the application database session (no ``PGVECTOR_DB_URL``)
or opens its own engine. Rows live in a ``document_chunk`` table with a
fixed vector dimension (``PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH``);
shorter embeddings are zero-padded, longer ones are rejected. Cosine
distance spans [2, 0]; it is converted to a [0, 1] score with 1 = best.
"""

import logging
from typing import Any, Dict, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    cast,
    column,
    create_engine,
    select,
    text,
    true,
    values,
)
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.pool import NullPool

from jyotigpt.config import PGVECTOR_DB_URL, PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.vector.main import GetResult, SearchResult, VectorItem

VECTOR_LENGTH = PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH
Base = declarative_base()

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class DocumentChunk(Base):
    """One vector row: text plus JSON metadata, keyed by collection."""

    __tablename__ = "document_chunk"

    id = Column(Text, primary_key=True)
    vector = Column(Vector(dim=VECTOR_LENGTH), nullable=True)
    collection_name = Column(Text, nullable=False)
    text = Column(Text, nullable=True)
    vmetadata = Column(MutableDict.as_mutable(JSONB), nullable=True)


class PgvectorClient:
    """CRUD/search client for a Postgres database with pgvector."""

    def __init__(self) -> None:
        # Without a dedicated URL, piggyback on the application database.
        if not PGVECTOR_DB_URL:
            from jyotigpt.internal.db import Session

            self.session = Session
        else:
            engine = create_engine(
                PGVECTOR_DB_URL, pool_pre_ping=True, poolclass=NullPool
            )
            SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
            )
            self.session = scoped_session(SessionLocal)

        try:
            # The extension, vector-dimension guard, table and indexes are
            # all set up lazily here so the client is usable immediately.
            self.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

            self.check_vector_length()

            connection = self.session.connection()
            Base.metadata.create_all(bind=connection)

            self.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_document_chunk_vector "
                    "ON document_chunk USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);"
                )
            )
            self.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_document_chunk_collection_name "
                    "ON document_chunk (collection_name);"
                )
            )
            self.session.commit()
            log.info("Initialization complete.")
        except Exception as e:
            self.session.rollback()
            log.exception(f"Error during initialization: {e}")
            raise

    # --- dimension handling ----------------------------------------------

    def check_vector_length(self) -> None:
        """Fail loudly if the existing column has a different dimension.

        Reflecting the table first means a fresh database skips the check.
        """
        metadata = MetaData()
        try:
            document_chunk_table = Table(
                "document_chunk", metadata, autoload_with=self.session.bind
            )
        except NoSuchTableError:
            return

        vector_column = document_chunk_table.columns["vector"]
        vector_type = vector_column.type
        if isinstance(vector_type, Vector):
            db_vector_length = vector_type.dim
            if db_vector_length != VECTOR_LENGTH:
                raise Exception(
                    f"VECTOR_LENGTH {VECTOR_LENGTH} does not match existing vector column dimension {db_vector_length}. "
                    "Cannot change vector size after initialization without migrating the data."
                )
        else:
            raise Exception("The 'vector' column exists but is not of type 'Vector'.")

    def adjust_vector_length(self, vector: List[float]) -> List[float]:
        """Pad short vectors with zeros; reject over-long ones."""
        current_length = len(vector)
        if current_length < VECTOR_LENGTH:
            vector += [0.0] * (VECTOR_LENGTH - current_length)
        elif current_length > VECTOR_LENGTH:
            raise Exception(
                f"Vector length {current_length} not supported. Max length must be <= {VECTOR_LENGTH}"
            )
        return vector

    # --- persistence -----------------------------------------------------

    def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        try:
            new_items = [
                DocumentChunk(
                    id=item["id"],
                    vector=self.adjust_vector_length(item["vector"]),
                    collection_name=collection_name,
                    text=item["text"],
                    vmetadata=item["metadata"],
                )
                for item in items
            ]
            self.session.bulk_save_objects(new_items)
            self.session.commit()
            log.info(
                f"Inserted {len(new_items)} items into collection '{collection_name}'."
            )
        except Exception as e:
            self.session.rollback()
            log.exception(f"Error during insert: {e}")
            raise

    def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        try:
            for item in items:
                vector = self.adjust_vector_length(item["vector"])
                existing = (
                    self.session.query(DocumentChunk)
                    .filter(DocumentChunk.id == item["id"])
                    .first()
                )
                if existing:
                    existing.vector = vector
                    existing.text = item["text"]
                    existing.vmetadata = item["metadata"]
                    existing.collection_name = collection_name
                else:
                    self.session.add(
                        DocumentChunk(
                            id=item["id"],
                            vector=vector,
                            collection_name=collection_name,
                            text=item["text"],
                            vmetadata=item["metadata"],
                        )
                    )
            self.session.commit()
            log.info(
                f"Upserted {len(items)} items into collection '{collection_name}'."
            )
        except Exception as e:
            self.session.rollback()
            log.exception(f"Error during upsert: {e}")
            raise

    # --- reads -----------------------------------------------------------

    def search(
        self,
        collection_name: str,
        vectors: List[List[float]],
        limit: Optional[int] = None,
    ) -> Optional[SearchResult]:
        """Nearest-neighbor lookup via a lateral join of query vectors."""
        try:
            if not vectors:
                return None

            vectors = [self.adjust_vector_length(vector) for vector in vectors]
            num_queries = len(vectors)

            def vector_expr(vector):
                return cast(array(vector), Vector(VECTOR_LENGTH))

            qid_col = column("qid", Integer)
            q_vector_col = column("q_vector", Vector(VECTOR_LENGTH))
            query_vectors = (
                values(qid_col, q_vector_col)
                .data(
                    [(idx, vector_expr(vector)) for idx, vector in enumerate(vectors)]
                )
                .alias("query_vectors")
            )

            subq = (
                select(
                    DocumentChunk.id,
                    DocumentChunk.text,
                    DocumentChunk.vmetadata,
                    DocumentChunk.vector.cosine_distance(
                        query_vectors.c.q_vector
                    ).label("distance"),
                )
                .where(DocumentChunk.collection_name == collection_name)
                .order_by(
                    DocumentChunk.vector.cosine_distance(query_vectors.c.q_vector)
                )
            )
            if limit is not None:
                subq = subq.limit(limit)
            subq = subq.lateral("result")

            stmt = (
                select(
                    query_vectors.c.qid,
                    subq.c.id,
                    subq.c.text,
                    subq.c.vmetadata,
                    subq.c.distance,
                )
                .select_from(query_vectors)
                .join(subq, true())
                .order_by(query_vectors.c.qid, subq.c.distance)
            )

            result_proxy = self.session.execute(stmt)
            results = result_proxy.all()

            ids = [[] for _ in range(num_queries)]
            distances = [[] for _ in range(num_queries)]
            documents = [[] for _ in range(num_queries)]
            metadatas = [[] for _ in range(num_queries)]

            if not results:
                return SearchResult(
                    ids=ids,
                    distances=distances,
                    documents=documents,
                    metadatas=metadatas,
                )

            for row in results:
                qid = int(row.qid)
                ids[qid].append(row.id)
                # pgvector cosine distance spans [2, 0]; flip to a [0, 1] score.
                distances[qid].append((2.0 - row.distance) / 2.0)
                documents[qid].append(row.text)
                metadatas[qid].append(row.vmetadata)

            return SearchResult(
                ids=ids, distances=distances, documents=documents, metadatas=metadatas
            )
        except Exception as e:
            log.exception(f"Error during search: {e}")
            return None

    def query(
        self, collection_name: str, filter: Dict[str, Any], limit: Optional[int] = None
    ) -> Optional[GetResult]:
        """Rows whose metadata matches every key in ``filter``."""
        try:
            query = self.session.query(DocumentChunk).filter(
                DocumentChunk.collection_name == collection_name
            )

            for key, value in filter.items():
                query = query.filter(DocumentChunk.vmetadata[key].astext == str(value))

            if limit is not None:
                query = query.limit(limit)

            results = query.all()
            if not results:
                return None

            return GetResult(
                ids=[[result.id for result in results]],
                documents=[[result.text for result in results]],
                metadatas=[[result.vmetadata for result in results]],
            )
        except Exception as e:
            log.exception(f"Error during query: {e}")
            return None

    def get(
        self, collection_name: str, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        """Everything in the collection (optionally capped at ``limit``)."""
        try:
            query = self.session.query(DocumentChunk).filter(
                DocumentChunk.collection_name == collection_name
            )
            if limit is not None:
                query = query.limit(limit)

            results = query.all()
            if not results:
                return None

            return GetResult(
                ids=[[result.id for result in results]],
                documents=[[result.text for result in results]],
                metadatas=[[result.vmetadata for result in results]],
            )
        except Exception as e:
            log.exception(f"Error during get: {e}")
            return None

    # --- writes ----------------------------------------------------------

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Delete a collection's rows by ``ids`` and/or a ``filter``.

        ``metadata`` is an accepted alias for ``filter`` — some callers pass
        the selector under that name.
        """
        try:
            effective_filter = filter or metadata
            query = self.session.query(DocumentChunk).filter(
                DocumentChunk.collection_name == collection_name
            )
            if ids:
                query = query.filter(DocumentChunk.id.in_(ids))
            if effective_filter:
                for key, value in effective_filter.items():
                    query = query.filter(
                        DocumentChunk.vmetadata[key].astext == str(value)
                    )
            deleted = query.delete(synchronize_session=False)
            self.session.commit()
            log.info(f"Deleted {deleted} items from collection '{collection_name}'.")
        except Exception as e:
            self.session.rollback()
            log.exception(f"Error during delete: {e}")
            raise

    def reset(self) -> None:
        """Wipe the whole ``document_chunk`` table."""
        try:
            deleted = self.session.query(DocumentChunk).delete()
            self.session.commit()
            log.info(
                f"Reset complete. Deleted {deleted} items from 'document_chunk' table."
            )
        except Exception as e:
            self.session.rollback()
            log.exception(f"Error during reset: {e}")
            raise

    def close(self) -> None:
        pass

    # --- collections -----------------------------------------------------

    def has_collection(self, collection_name: str) -> bool:
        try:
            return (
                self.session.query(DocumentChunk)
                .filter(DocumentChunk.collection_name == collection_name)
                .first()
                is not None
            )
        except Exception as e:
            log.exception(f"Error checking collection existence: {e}")
            return False

    def delete_collection(self, collection_name: str) -> None:
        """Drop every row belonging to the collection."""
        self.delete(collection_name)
        log.info(f"Collection '{collection_name}' deleted.")
