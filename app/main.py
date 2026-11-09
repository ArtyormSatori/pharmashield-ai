"""
PharmaShield AI - FastAPI Application Server
Entrypoint providing high-performance REST APIs for multi-drug regimen safety analysis,
neural entity resolution, interactive benchmarking, and serving the clinical UI.
"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.schemas import (
    AnalyzeRequest,
    AnalysisResponse,
    PatientProfile,
    SeverityLevel,
)
from app.core.pharmacology_db import DRUGS_DB
from app.core.semantic_matcher import SemanticDrugMatcher
from app.core.interaction_engine import ClinicalInteractionEngine
from app.core.responsible_ai import ResponsibleAIGuard

# Initialize core services
app = FastAPI(
    title="PharmaShield AI",
    description="Clinical Prescription Safety & Drug-Drug Interaction Intelligence System",
    version="1.0.0",
)

# Enable CORS for local testing and web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Lazy singletons
_matcher: Optional[SemanticDrugMatcher] = None
_engine: Optional[ClinicalInteractionEngine] = None
_guard: Optional[ResponsibleAIGuard] = None


def get_matcher() -> SemanticDrugMatcher:
    global _matcher
    if _matcher is None:
        _matcher = SemanticDrugMatcher(use_neural=True)
    return _matcher


def get_engine() -> ClinicalInteractionEngine:
    global _engine
    if _engine is None:
        _engine = ClinicalInteractionEngine()
    return _engine


def get_guard() -> ResponsibleAIGuard:
    global _guard
    if _guard is None:
        _guard = ResponsibleAIGuard()
    return _guard


@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index file not found")
    return FileResponse(index_file)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "PharmaShield AI",
        "version": "1.0.0",
        "total_active_compounds": len(DRUGS_DB),
        "ai_engine": "Hybrid BGE-small-en-v1.5 + Deterministic Pharmacology Knowledge Graph",
        "privacy_guarantee": "100% On-Device / Zero Outbound Egress",
    }


@app.get("/api/drugs")
async def search_drugs(q: str = Query(..., min_length=1, description="Search query")):
    matcher = get_matcher()
    results = matcher.search_drugs(q, limit=12)
    return {"query": q, "count": len(results), "results": results}


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_regimen(request: AnalyzeRequest):
    t0 = time.perf_counter()
    matcher = get_matcher()
    engine = get_engine()
    guard = get_guard()

    if not request.drugs:
        raise HTTPException(status_code=400, detail="Must provide at least one drug name.")

    resolved_drugs: List[Dict[str, Any]] = []
    canonical_ids: List[str] = []
    unresolved_queries: List[str] = []

    for drug_query in request.drugs:
        match_result = matcher.resolve_drug(drug_query)
        if match_result:
            drug_id, conf, method = match_result
            info = DRUGS_DB[drug_id]
            canonical_ids.append(drug_id)
            resolved_drugs.append({
                "query": drug_query,
                "canonical_id": drug_id,
                "name": info["name"],
                "class": info["class"],
                "brand_names": info.get("brand_names", []),
                "resolution_confidence": conf,
                "match_method": method,
                "standard_dosage": info.get("standard_dosage", "N/A"),
            })
        else:
            unresolved_queries.append(drug_query)
            resolved_drugs.append({
                "query": drug_query,
                "canonical_id": None,
                "name": drug_query,
                "class": "Unknown / Unverified Compound",
                "brand_names": [],
                "resolution_confidence": 0.0,
                "match_method": "unresolved",
                "standard_dosage": "N/A",
            })

    # Evaluate using clinical interaction engine
    patient = request.patient or PatientProfile()
    interactions, cumulative, alternatives, guidance, max_severity = engine.evaluate_regime(
        canonical_ids, patient
    )

    if unresolved_queries:
        guidance.append(
            f"ℹ️ Unverified Substances: The following queries could not be resolved to verified pharmaceutical compounds: {', '.join(unresolved_queries)}. Exercise clinical caution regarding unstandardized supplements or herbal products."
        )

    # Determine overall status text
    overall_status = "SAFE"
    if max_severity == SeverityLevel.CONTRAINDICATED:
        overall_status = "CRITICAL_CONTRAINDICATION"
    elif max_severity == SeverityLevel.SEVERE:
        overall_status = "HIGH_RISK"
    elif max_severity == SeverityLevel.MODERATE:
        overall_status = "CAUTION"
    elif max_severity == SeverityLevel.MINOR:
        overall_status = "MINOR_INTERACTION"

    # Verify grounding
    disclosure = guard.get_disclosure()
    t1 = time.perf_counter()
    latency_ms = round((t1 - t0) * 1000.0, 2)

    return AnalysisResponse(
        resolved_drugs=resolved_drugs,
        patient_profile=patient,
        overall_safety_status=overall_status,
        max_severity=max_severity,
        interactions=interactions,
        cumulative_risks=cumulative,
        alternatives=alternatives,
        patient_friendly_guidance=guidance,
        responsible_ai=disclosure,
        latency_ms=latency_ms,
    )


@app.get("/api/benchmark")
async def get_benchmark():
    benchmark_path = PROJECT_ROOT / "BENCHMARK_RESULTS.json"
    if not benchmark_path.exists():
        from eval_benchmark import run_benchmark
        return run_benchmark()

    import json
    with open(benchmark_path, "r") as f:
        data = json.load(f)
    return data


# Mount static directory
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
