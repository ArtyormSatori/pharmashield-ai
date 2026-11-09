#!/usr/bin/env python3
"""
PharmaShield AI - Empirical Clinical Evaluation & Benchmark
Evaluates detection accuracy, clinical sensitivity, specificity, F1-score,
and latency on curated real-world clinical drug-drug interaction pairs.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.schemas import PatientProfile, SeverityLevel
from app.core.interaction_engine import ClinicalInteractionEngine
from app.core.pharmacology_db import DRUGS_DB


def run_benchmark():
    benchmark_file = PROJECT_ROOT / "data" / "test_pairs_benchmark.json"
    if not benchmark_file.exists():
        print(f"Error: Benchmark file {benchmark_file} not found.")
        sys.exit(1)

    with open(benchmark_file, "r") as f:
        test_pairs = json.load(f)

    engine = ClinicalInteractionEngine()
    patient = PatientProfile(age=45, eGFR=90.0)

    total_pairs = len(test_pairs)
    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0
    exact_severity_matches = 0

    latencies = []
    results_detail = []

    print(f"\n=======================================================")
    print(f"  PHARMASHIELD AI - CLINICAL INTERACTION BENCHMARK     ")
    print(f"  Evaluating {total_pairs} verified clinical drug pairs...     ")
    print(f"=======================================================\n")

    for item in test_pairs:
        d1 = item["drug_a"]
        d2 = item["drug_b"]
        expected = item["expected_severity"]
        category = item.get("category", "general")

        t0 = time.perf_counter()
        interactions, cumulative, alts, guidance, max_sev = engine.evaluate_regime([d1, d2], patient)
        t1 = time.perf_counter()
        lat_ms = (t1 - t0) * 1000.0
        latencies.append(lat_ms)

        predicted_severity = max_sev.value

        is_dangerous_expected = expected in ["CONTRAINDICATED", "SEVERE", "MODERATE", "MINOR"]
        is_dangerous_predicted = predicted_severity in ["CONTRAINDICATED", "SEVERE", "MODERATE", "MINOR"]

        if is_dangerous_expected and is_dangerous_predicted:
            true_positives += 1
        elif not is_dangerous_expected and is_dangerous_predicted:
            false_positives += 1
        elif not is_dangerous_expected and not is_dangerous_predicted:
            true_negatives += 1
        elif is_dangerous_expected and not is_dangerous_predicted:
            false_negatives += 1

        is_exact = (predicted_severity == expected)
        if is_exact:
            exact_severity_matches += 1

        status_mark = "PASS" if is_exact or (is_dangerous_expected == is_dangerous_predicted) else "FAIL"

        results_detail.append({
            "drug_a": d1,
            "drug_b": d2,
            "category": category,
            "expected_severity": expected,
            "predicted_severity": predicted_severity,
            "is_exact_severity": is_exact,
            "status": status_mark,
            "latency_ms": round(lat_ms, 3)
        })

        print(f"[{status_mark}] {d1:15} + {d2:15} | Expected: {expected:14} | Predicted: {predicted_severity:14} ({lat_ms:.2f}ms)")

    # Compute Statistical Metrics
    accuracy = (true_positives + true_negatives) / total_pairs if total_pairs > 0 else 0.0
    sensitivity = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    specificity = true_negatives / (true_negatives + false_positives) if (true_negatives + false_positives) > 0 else 0.0
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    f1_score = (2 * precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0.0
    exact_acc = exact_severity_matches / total_pairs if total_pairs > 0 else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    print("\n-------------------------------------------------------")
    print(f"BENCHMARK SUMMARY METRICS:")
    print(f"  Total Test Cases:            {total_pairs}")
    print(f"  True Positives (Alerts):     {true_positives}")
    print(f"  True Negatives (Safe):       {true_negatives}")
    print(f"  False Positives:             {false_positives}")
    print(f"  False Negatives:             {false_negatives}")
    print(f"  Sensitivity (Recall):        {sensitivity * 100:.2f}%")
    print(f"  Specificity:                 {specificity * 100:.2f}%")
    print(f"  Precision:                   {precision * 100:.2f}%")
    print(f"  F1-Score:                    {f1_score * 100:.2f}%")
    print(f"  Binary Detection Accuracy:   {accuracy * 100:.2f}%")
    print(f"  Exact Severity Grade Acc:    {exact_acc * 100:.2f}%")
    print(f"  Mean Evaluation Latency:     {avg_latency:.3f} ms")
    print("-------------------------------------------------------\n")

    summary_output = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_test_pairs": total_pairs,
        "metrics": {
            "binary_accuracy_pct": round(accuracy * 100.0, 2),
            "sensitivity_recall_pct": round(sensitivity * 100.0, 2),
            "specificity_pct": round(specificity * 100.0, 2),
            "precision_pct": round(precision * 100.0, 2),
            "f1_score_pct": round(f1_score * 100.0, 2),
            "exact_severity_accuracy_pct": round(exact_acc * 100.0, 2),
            "mean_latency_ms": round(avg_latency, 3),
            "true_positives": true_positives,
            "true_negatives": true_negatives,
            "false_positives": false_positives,
            "false_negatives": false_negatives
        },
        "results": results_detail
    }

    output_path = PROJECT_ROOT / "BENCHMARK_RESULTS.json"
    with open(output_path, "w") as out_f:
        json.dump(summary_output, out_f, indent=2)

    print(f"Results successfully saved to {output_path}")
    return summary_output


if __name__ == "__main__":
    run_benchmark()
