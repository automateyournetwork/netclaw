"""Local cross-encoder reranking for rag-mcp (FR-022, FR-024).

Reranks the fused hybrid candidates down to top-k on CPU. Disableable via
RAG_RERANK_ENABLED for low-resource hosts (fusion-order passthrough).
Candidates scoring below the relevance floor are flagged low_confidence —
never dropped — so the agent's critique step has signal.
"""

import logging
import math
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


class Reranker:
    def __init__(self, model_name: str, enabled: bool = True):
        self.model_name = model_name
        self.enabled = enabled
        self._model = None
        self._failed = False

    def _load(self):
        if self._model is not None or self._failed:
            return self._model
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        except Exception as exc:
            log.warning(f"Reranker '{self.model_name}' unavailable — passthrough mode: {exc}")
            self._failed = True
        return self._model

    def rerank(
        self, query: str, candidates: List[Dict], k: int, relevance_floor: float
    ) -> List[Dict]:
        """candidates: [{chunk_id, text, metadata, rrf_score, dense_score}].
        Returns top-k as [{..., score, low_confidence}]. With reranking off or
        unavailable, fusion order is kept and dense cosine drives the floor."""
        if not candidates:
            return []

        model = self._load() if self.enabled else None
        if model is not None:
            pairs = [(query, c["text"]) for c in candidates]
            raw = model.predict(pairs)
            scored = []
            for c, logit in zip(candidates, raw):
                score = 1.0 / (1.0 + math.exp(-float(logit)))  # sigmoid -> [0,1]
                scored.append({**c, "score": round(score, 4)})
            scored.sort(key=lambda c: -c["score"])
        else:
            # Passthrough: fusion order, dense cosine as the confidence signal
            scored = [{**c, "score": c["dense_score"]} for c in candidates]

        top = scored[:k]
        for c in top:
            c["low_confidence"] = c["score"] < relevance_floor
        return top
