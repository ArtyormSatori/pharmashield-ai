"""
PharmaShield AI - Neural Semantic Matcher
Hybrid Entity Resolution combining deterministic alias/brand normalization
with dense neural text embeddings (BAAI/bge-small-en-v1.5) to resolve trade names,
generic names, colloquial queries, and minor misspellings to canonical pharmacology entities.
"""

import os
import re
import math
from typing import Dict, Any, List, Optional, Tuple
from app.core.pharmacology_db import DRUGS_DB

# Global in-memory cache for embeddings
_MODEL = None
_TOKENIZER = None
_DRUG_EMBEDDINGS = None
_DRUG_KEYS_INDEX: List[str] = []
_INDEX_TEXTS: List[str] = []


def _normalize_string(text: str) -> str:
    """Normalize string for direct dictionary lookup."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return " ".join(clean.split())


# Pre-build inverted alias map from brand names and synonyms
ALIAS_MAP: Dict[str, str] = {}
for drug_id, drug_data in DRUGS_DB.items():
    ALIAS_MAP[drug_id.lower()] = drug_id
    ALIAS_MAP[_normalize_string(drug_data["name"])] = drug_id
    for brand in drug_data.get("brand_names", []):
        ALIAS_MAP[_normalize_string(brand)] = drug_id
        # Also index single words for multi-word brands
        for part in brand.split():
            clean_part = _normalize_string(part)
            if len(clean_part) >= 4 and clean_part not in ALIAS_MAP:
                ALIAS_MAP[clean_part] = drug_id


def _lazy_init_neural_model():
    """Lazily load BGE-small-en-v1.5 embedding model once."""
    global _MODEL, _TOKENIZER, _DRUG_EMBEDDINGS, _DRUG_KEYS_INDEX, _INDEX_TEXTS
    if _MODEL is not None:
        return

    try:
        import torch
        from transformers import AutoTokenizer, AutoModel

        model_name = "BAAI/bge-small-en-v1.5"
        _TOKENIZER = AutoTokenizer.from_pretrained(model_name)
        _MODEL = AutoModel.from_pretrained(model_name)
        _MODEL.eval()

        # Build drug index texts for neural matching
        _DRUG_KEYS_INDEX = []
        _INDEX_TEXTS = []
        for drug_id, drug_data in DRUGS_DB.items():
            brands = ", ".join(drug_data.get("brand_names", []))
            text = f"{drug_data['name']} (brands: {brands}) - {drug_data['class']}"
            _DRUG_KEYS_INDEX.append(drug_id)
            _INDEX_TEXTS.append(text)

        # Precompute index embeddings
        with torch.no_grad():
            inputs = _TOKENIZER(_INDEX_TEXTS, padding=True, truncation=True, max_length=64, return_tensors="pt")
            outputs = _MODEL(**inputs)
            # CLS token pooling with L2 normalization
            emb = outputs.last_hidden_state[:, 0]
            _DRUG_EMBEDDINGS = torch.nn.functional.normalize(emb, p=2, dim=1)
    except Exception as e:
        # Fallback to deterministic matching if neural model cannot load
        _MODEL = False


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticDrugMatcher:
    """Hybrid matcher resolving drug queries to canonical IDs."""

    def __init__(self, use_neural: bool = True):
        self.use_neural = use_neural
        if use_neural:
            _lazy_init_neural_model()

    def resolve_drug(self, query: str) -> Optional[Tuple[str, float, str]]:
        """
        Resolves query to (canonical_drug_id, confidence, match_method).
        Returns None if not recognized.
        """
        if not query or not query.strip():
            return None

        clean_query = _normalize_string(query)

        # 1. Exact alias / brand lookup
        if clean_query in ALIAS_MAP:
            drug_id = ALIAS_MAP[clean_query]
            return drug_id, 1.0, "exact_alias"

        # Check partial token match
        tokens = clean_query.split()
        for tok in tokens:
            if tok in ALIAS_MAP:
                return ALIAS_MAP[tok], 0.95, "token_alias"

        # 2. Substring matching in names and brands
        for drug_id, data in DRUGS_DB.items():
            if drug_id in clean_query or clean_query in drug_id:
                return drug_id, 0.90, "substring_match"
            for brand in data.get("brand_names", []):
                clean_brand = _normalize_string(brand)
                if clean_brand in clean_query or clean_query in clean_brand:
                    return drug_id, 0.90, "brand_substring"

        # 3. Neural Dense Vector Similarity Match (BGE-small-en-v1.5)
        global _MODEL, _TOKENIZER, _DRUG_EMBEDDINGS, _DRUG_KEYS_INDEX
        if self.use_neural and _MODEL:
            try:
                import torch
                with torch.no_grad():
                    inputs = _TOKENIZER([f"medication: {query}"], padding=True, truncation=True, max_length=64, return_tensors="pt")
                    outputs = _MODEL(**inputs)
                    query_emb = torch.nn.functional.normalize(outputs.last_hidden_state[:, 0], p=2, dim=1)
                    sims = torch.mm(query_emb, _DRUG_EMBEDDINGS.t()).squeeze(0)
                    best_score, best_idx = torch.max(sims, dim=0)
                    score = float(best_score.item())
                    if score >= 0.72:
                        matched_id = _DRUG_KEYS_INDEX[int(best_idx.item())]
                        return matched_id, round(score, 4), "neural_dense_bge"
            except Exception:
                pass

        return None

    def search_drugs(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search and autocomplete drugs for the UI."""
        clean = _normalize_string(query)
        matches = []
        seen = set()

        for drug_id, data in DRUGS_DB.items():
            name_clean = _normalize_string(data["name"])
            brands_clean = [_normalize_string(b) for b in data.get("brand_names", [])]

            score = 0
            if clean == drug_id or clean == name_clean:
                score = 100
            elif name_clean.startswith(clean) or any(b.startswith(clean) for b in brands_clean):
                score = 80
            elif clean in name_clean or any(clean in b for b in brands_clean):
                score = 60
            elif clean in _normalize_string(data["class"]):
                score = 40

            if score > 0 and drug_id not in seen:
                seen.add(drug_id)
                matches.append({
                    "id": drug_id,
                    "name": data["name"],
                    "brand_names": data.get("brand_names", []),
                    "class": data["class"],
                    "standard_dosage": data.get("standard_dosage", "N/A"),
                    "score": score
                })

        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:limit]
