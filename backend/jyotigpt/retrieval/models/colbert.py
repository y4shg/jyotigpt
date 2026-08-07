"""ColBERT late-interaction re-ranking model.

Wraps the ``colbert`` package's checkpoint so that a set of (query,
document) pairs can be scored for retrieval. The model is loaded lazily
by the retrieval service — this module is only imported on demand.
"""

import logging
import os

import numpy as np
import torch
from colbert.infra import ColBERTConfig
from colbert.modeling.checkpoint import Checkpoint

from jyotigpt.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class ColBERT:
    """Late-interaction re-ranker around a ColBERT checkpoint."""

    def __init__(self, name, **kwargs) -> None:
        log.info(f"ColBERT: Loading model {name}")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        if kwargs.get("env") == "docker":
            # The torch C++ extension can be left in a stale, half-built state
            # inside the Docker image; a leftover lock file makes it fail to
            # load at runtime, so clear it before checkpoint loading.
            lock_file = (
                "/root/.cache/torch_extensions/py311_cpu/segmented_maxsim_cpp/lock"
            )
            if os.path.exists(lock_file):
                os.remove(lock_file)

        self.ckpt = Checkpoint(
            name,
            colbert_config=ColBERTConfig(model_name=name),
        ).to(self.device)

    def calculate_similarity_scores(self, query_embeddings, document_embeddings):
        """MaxSim score of each query against each document, softmax-normalized."""
        query_embeddings = query_embeddings.to(self.device)
        document_embeddings = document_embeddings.to(self.device)

        # Validate dimensions to ensure compatibility.
        if query_embeddings.dim() != 3:
            raise ValueError(
                f"Expected query embeddings to have 3 dimensions, but got {query_embeddings.dim()}."
            )
        if document_embeddings.dim() != 3:
            raise ValueError(
                f"Expected document embeddings to have 3 dimensions, but got {document_embeddings.dim()}."
            )
        if query_embeddings.size(0) not in [1, document_embeddings.size(0)]:
            raise ValueError(
                "There should be either one query or queries equal to the number of documents."
            )

        # Permute query embeddings (B, F, T) -> (B, T, F) so the matmul
        # produces per-token similarity maps, then take the best token match
        # per query token (MaxSim) and sum over the query tokens.
        transposed_query_embeddings = query_embeddings.permute(0, 2, 1)
        computed_scores = torch.matmul(document_embeddings, transposed_query_embeddings)
        maximum_scores = torch.max(computed_scores, dim=1).values
        final_scores = maximum_scores.sum(dim=1)

        normalized_scores = torch.softmax(final_scores, dim=0)

        return normalized_scores.detach().cpu().numpy().astype(np.float32)

    def predict(self, sentences):
        """Score ``[(query, document), ...]`` pairs with the ColBERT model."""
        query = sentences[0][0]
        docs = [pair[1] for pair in sentences]

        embedded_docs = self.ckpt.docFromText(docs, bsize=32)[0]
        embedded_query = self.ckpt.queryFromText([query], bsize=32)[0]

        scores = self.calculate_similarity_scores(
            embedded_query.unsqueeze(0), embedded_docs
        )

        return scores
