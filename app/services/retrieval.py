"""Deterministic multilingual tokenization and local hash embeddings."""

from __future__ import annotations

import hashlib
import math
import re

TOKEN_PATTERN = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
VECTOR_SIZE = 256


def hash_embedding(text: str) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    tokens = [token.casefold() for token in TOKEN_PATTERN.findall(text) if len(token) > 1]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % VECTOR_SIZE
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def lexical_score(query: str, document: str) -> float:
    query_tokens = {token.casefold() for token in TOKEN_PATTERN.findall(query) if len(token) > 1}
    if not query_tokens:
        return 0.0
    document_tokens = {
        token.casefold() for token in TOKEN_PATTERN.findall(document) if len(token) > 1
    }
    return len(query_tokens.intersection(document_tokens)) / len(query_tokens)
