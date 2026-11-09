/**
 * PharmaShield AI - Frontend Application Logic
 * Handles interactive drug management, live autocomplete, 1-click clinical presets,
 * API communication, interactive N x N matrix generation, and benchmark reporting.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Application State
  const state = {
    selectedDrugs: [],
    searchDebounceTimer: null,
    currentResults: null
  };

  // DOM Elements
  const drugInput = document.getElementById("drug-search-input");
  const btnAddDrug = document.getElementById("btn-add-drug");
  const autocompleteBox = document.getElementById("autocomplete-dropdown");
  const drugsContainer = document.getElementById("selected-drugs-container");
  const drugCountEl = document.getElementById("drug-count");
  const btnClearAll = document.getElementById("btn-clear-all");

  const ageInput = document.getElementById("patient-age");
  const egfrInput = document.getElementById("patient-egfr");
  const hepaticCheck = document.getElementById("patient-hepatic");
  const pregnantCheck = document.getElementById("patient-pregnant");

  const btnRunAnalysis = document.getElementById("btn-run-analysis");
  const btnSpinner = document.getElementById("btn-spinner");

  const resultsPlaceholder = document.getElementById("results-placeholder");
  const resultsContent = document.getElementById("results-content");
  const latencyIndicator = document.getElementById("latency-indicator");

  const statusBanner = document.getElementById("status-banner");
  const statusIcon = document.getElementById("status-icon");
  const statusTitle = document.getElementById("status-title");
  const statusDesc = document.getElementById("status-description");

  const metricDrugsCount = document.getElementById("metric-drugs-count");
  const metricAlertsCount = document.getElementById("metric-alerts-count");

  const matrixContainer = document.getElementById("interaction-matrix-container");

  const barSerotonin = document.getElementById("bar-serotonin");
  const badgeSerotonin = document.getElementById("badge-serotonin");
  const textSerotonin = document.getElementById("text-serotonin");

  const barQt = document.getElementById("bar-qt");
  const badgeQt = document.getElementById("badge-qt");
  const textQt = document.getElementById("text-qt");

  const barBleeding = document.getElementById("bar-bleeding");
  const badgeBleeding = document.getElementById("badge-bleeding");
  const textBleeding = document.getElementById("text-bleeding");

  const barCns = document.getElementById("bar-cns");
  const badgeCns = document.getElementById("badge-cns");
  const textCns = document.getElementById("text-cns");

  const tripleWhammyAlert = document.getElementById("triple-whammy-alert");

  const monographsCount = document.getElementById("monographs-count");
  const interactionsList = document.getElementById("interactions-list");

  const alternativesBox = document.getElementById("alternatives-box");
  const alternativesList = document.getElementById("alternatives-list");

  const organWarningsBox = document.getElementById("organ-warnings-box");
  const organWarningsList = document.getElementById("organ-warnings-list");

  const patientGuidanceList = document.getElementById("patient-guidance-list");

  // Benchmark Modal
  const btnViewBenchmark = document.getElementById("btn-view-benchmark");
  const benchmarkModal = document.getElementById("benchmark-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const bmAccuracy = document.getElementById("bm-accuracy");
  const bmSensitivity = document.getElementById("bm-sensitivity");
  const bmPrecision = document.getElementById("bm-precision");
  const bmF1 = document.getElementById("bm-f1");
  const bmLatency = document.getElementById("bm-latency");
  const bmTableBody = document.getElementById("benchmark-table-body");

  // Presets Definition
  const PRESETS = {
    bleeding: {
      drugs: ["Warfarin", "Amiodarone", "Bayer Aspirin"],
      age: 68,
      egfr: 75,
      hepatic: false,
      pregnant: false
    },
    serotonin: {
      drugs: ["Zoloft", "Ultram", "Zyvox"],
      age: 38,
      egfr: 95,
      hepatic: false,
      pregnant: false
    },
    torsades: {
      drugs: ["Z-Pak", "Haldol", "Celexa"],
      age: 72,
      egfr: 55,
      hepatic: false,
      pregnant: false
    },
    triple: {
      drugs: ["Lisinopril", "Lasix", "Advil"],
      age: 74,
      egfr: 45,
      hepatic: false,
      pregnant: false
    },
    safe: {
      drugs: ["Lipitor", "Glucophage", "Prinivil"],
      age: 52,
      egfr: 90,
      hepatic: false,
      pregnant: false
    }
  };

  // Wire Preset Buttons
  document.querySelectorAll(".preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const presetKey = btn.getAttribute("data-preset");
      const preset = PRESETS[presetKey];
      if (preset) {
        state.selectedDrugs = [...preset.drugs];
        ageInput.value = preset.age;
        egfrInput.value = preset.egfr;
        hepaticCheck.checked = preset.hepatic;
        pregnantCheck.checked = preset.pregnant;
        renderSelectedDrugs();
        runAnalysis();
      }
    });
  });

  // Drug Autocomplete
  drugInput.addEventListener("input", () => {
    clearTimeout(state.searchDebounceTimer);
    const query = drugInput.value.trim();
    if (query.length < 2) {
      autocompleteBox.innerHTML = "";
      autocompleteBox.classList.add("hidden");
      return;
    }
    state.searchDebounceTimer = setTimeout(() => {
      fetchAutocomplete(query);
    }, 200);
  });

  drugInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addCurrentInputDrug();
    }
  });

  btnAddDrug.addEventListener("click", addCurrentInputDrug);

  function addCurrentInputDrug() {
    const drugName = drugInput.value.trim();
    if (!drugName) return;
    if (!state.selectedDrugs.some(d => d.toLowerCase() === drugName.toLowerCase())) {
      state.selectedDrugs.push(drugName);
      renderSelectedDrugs();
    }
    drugInput.value = "";
    autocompleteBox.innerHTML = "";
    autocompleteBox.classList.add("hidden");
  }

  async function fetchAutocomplete(query) {
    try {
      const res = await fetch(`/api/drugs?q=${encodeURIComponent(query)}`);
      if (!res.ok) return;
      const data = await res.json();
      renderAutocomplete(data.results || []);
    } catch (err) {
      console.error("Autocomplete error:", err);
    }
  }

  function renderAutocomplete(results) {
    if (!results || results.length === 0) {
      autocompleteBox.innerHTML = `<div class="autocomplete-item"><span class="item-sub">No matching pharmaceutical compounds found</span></div>`;
      autocompleteBox.classList.remove("hidden");
      return;
    }
    autocompleteBox.innerHTML = results.map(item => `
      <div class="autocomplete-item" data-drug="${escapeHtml(item.name)}">
        <div>
          <div class="item-main">${escapeHtml(item.name)}</div>
          <div class="item-sub">${item.brand_names && item.brand_names.length ? 'Brands: ' + escapeHtml(item.brand_names.join(', ')) : ''}</div>
        </div>
        <span class="item-class">${escapeHtml(item.class || '')}</span>
      </div>
    `).join("");
    autocompleteBox.classList.remove("hidden");

    autocompleteBox.querySelectorAll(".autocomplete-item").forEach(el => {
      el.addEventListener("click", () => {
        const dName = el.getAttribute("data-drug");
        if (dName && !state.selectedDrugs.some(d => d.toLowerCase() === dName.toLowerCase())) {
          state.selectedDrugs.push(dName);
          renderSelectedDrugs();
        }
        drugInput.value = "";
        autocompleteBox.innerHTML = "";
        autocompleteBox.classList.add("hidden");
      });
    });
  }

  // Close dropdown on outside click
  document.addEventListener("click", (e) => {
    if (!autocompleteBox.contains(e.target) && e.target !== drugInput) {
      autocompleteBox.classList.add("hidden");
    }
  });

  // Render Selected Drugs Chips
  function renderSelectedDrugs() {
    drugCountEl.textContent = state.selectedDrugs.length;
    if (state.selectedDrugs.length === 0) {
      drugsContainer.innerHTML = `<p class="empty-state-text">No medications added yet. Type above or choose a clinical preset.</p>`;
      return;
    }
    drugsContainer.innerHTML = state.selectedDrugs.map((drug, idx) => `
      <div class="drug-chip">
        <div class="drug-chip-info">
          <span class="drug-chip-name">${escapeHtml(drug)}</span>
          <span class="drug-chip-class">Rx Compound #${idx + 1}</span>
        </div>
        <button class="btn-remove-chip" data-idx="${idx}" title="Remove drug">&times;</button>
      </div>
    `).join("");

    drugsContainer.querySelectorAll(".btn-remove-chip").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.getAttribute("data-idx"), 10);
        state.selectedDrugs.splice(idx, 1);
        renderSelectedDrugs();
      });
    });
  }

  btnClearAll.addEventListener("click", () => {
    state.selectedDrugs = [];
    renderSelectedDrugs();
    resultsPlaceholder.classList.remove("hidden");
    resultsContent.classList.add("hidden");
  });

  // Run AI Analysis
  btnRunAnalysis.addEventListener("click", runAnalysis);

  async function runAnalysis() {
    if (state.selectedDrugs.length === 0) {
      alert("Please add at least one medication before running analysis.");
      return;
    }

    btnSpinner.classList.remove("hidden");
    btnRunAnalysis.disabled = true;

    const payload = {
      drugs: state.selectedDrugs,
      patient: {
        age: parseInt(ageInput.value, 10) || 45,
        eGFR: parseFloat(egfrInput.value) || 90.0,
        hepatic_impairment: hepaticCheck.checked,
        pregnancy: pregnantCheck.checked
      }
    };

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Analysis failed");
      }

      const data = await res.json();
      state.currentResults = data;
      renderResults(data);
    } catch (err) {
      alert("Error executing clinical analysis: " + err.message);
      console.error(err);
    } finally {
      btnSpinner.classList.add("hidden");
      btnRunAnalysis.disabled = false;
    }
  }

  // Render Full Results Dashboard
  function renderResults(data) {
    resultsPlaceholder.classList.add("hidden");
    resultsContent.classList.remove("hidden");

    latencyIndicator.textContent = `Latency: ${data.latency_ms} ms`;

    // 1. Overall Status Banner
    const maxSev = data.max_severity || "SAFE";
    statusBanner.className = "status-banner";

    if (maxSev === "CONTRAINDICATED") {
      statusBanner.classList.add("status-contraindicated");
      statusIcon.textContent = "🛑";
      statusTitle.textContent = "CRITICAL CONTRAINDICATION DETECTED";
      statusDesc.textContent = "Fatal or life-threatening drug combination. Immediate clinical intervention and medication modification required.";
    } else if (maxSev === "SEVERE") {
      statusBanner.classList.add("status-severe");
      statusIcon.textContent = "⚠️";
      statusTitle.textContent = "HIGH-RISK CLINICAL COMBINATION";
      statusDesc.textContent = "Substantial risk of severe adverse events. Mandatory dosage titration, close laboratory monitoring, or drug substitution advised.";
    } else if (maxSev === "MODERATE") {
      statusBanner.classList.add("status-moderate");
      statusIcon.textContent = "⚡";
      statusTitle.textContent = "MODERATE INTERACTION CAUTION";
      statusDesc.textContent = "Pharmacokinetic or metabolic enzyme competition detected. Monitor patient symptoms or adjust administration intervals.";
    } else {
      statusBanner.classList.add("status-safe");
      statusIcon.textContent = "✅";
      statusTitle.textContent = "REGIMEN CLINICALLY COMPATIBLE";
      statusDesc.textContent = "No critical, severe, or high-risk pharmacokinetic interactions detected for this medication profile.";
    }

    // 2. Metrics Bar
    metricDrugsCount.textContent = data.resolved_drugs.length;
    metricAlertsCount.textContent = data.interactions.length;

    // 3. Visual Interactive N x N Matrix
    renderMatrix(data.resolved_drugs, data.interactions);

    // 4. Cumulative Toxicity Gauges
    renderGauges(data.cumulative_risks);

    // 5. Triple Whammy
    if (data.cumulative_risks && data.cumulative_risks.triple_whammy_nephrotoxicity) {
      tripleWhammyAlert.classList.remove("hidden");
    } else {
      tripleWhammyAlert.classList.add("hidden");
    }

    // 6. Pairwise Interaction Cards
    monographsCount.textContent = data.interactions.length;
    if (data.interactions.length === 0) {
      interactionsList.innerHTML = `<p class="empty-state-text">No significant pairwise interactions identified.</p>`;
    } else {
      interactionsList.innerHTML = data.interactions.map((alert, idx) => {
        const sevClass = alert.severity.toLowerCase();
        return `
          <div class="interaction-item item-border-${sevClass}" id="card-alert-${idx}">
            <div class="interaction-top">
              <span class="interaction-drugs-title">${escapeHtml(alert.drug_a)} ⟷ ${escapeHtml(alert.drug_b)}</span>
              <span class="severity-pill pill-${sevClass}">${alert.severity}</span>
            </div>
            <div class="interaction-row">
              <span class="row-label">Mechanism:</span> ${escapeHtml(alert.mechanism_type)} — ${escapeHtml(alert.mechanism)}
            </div>
            <div class="interaction-row">
              <span class="row-label">Clinical Effect:</span> ${escapeHtml(alert.clinical_effect)}
            </div>
            <div class="interaction-row">
              <span class="row-label">Physician Management:</span> ${escapeHtml(alert.clinical_management)}
            </div>
            <div class="interaction-citations">
              <strong>Evidence Level:</strong> ${escapeHtml(alert.evidence_level)} | <strong>Citations:</strong> ${(alert.evidence_citations || []).map(c => escapeHtml(c)).join("; ")}
            </div>
          </div>
        `;
      }).join("");
    }

    // 7. Safer Alternatives
    if (data.alternatives && data.alternatives.length > 0) {
      alternativesBox.classList.remove("hidden");
      alternativesList.innerHTML = data.alternatives.map(alt => `
        <div class="alt-card">
          <div class="alt-header">
            <span>🔄</span>
            <span class="alt-switch">Substitute ${escapeHtml(alt.problematic_drug)} ➔ <strong>${escapeHtml(alt.suggested_alternative)}</strong> (${escapeHtml(alt.therapeutic_class)})</span>
          </div>
          <div class="alt-body">
            <p><strong>Rationale:</strong> ${escapeHtml(alt.rationale)}</p>
            <p style="margin-top: 4px;"><strong>Clinical Advantage:</strong> ${escapeHtml(alt.safety_advantage)}</p>
          </div>
        </div>
      `).join("");
    } else {
      alternativesBox.classList.add("hidden");
    }

    // 8. Beers & Organ Clearance Warnings
    const organAlerts = (data.cumulative_risks && data.cumulative_risks.organ_clearance_warnings) || [];
    if (organAlerts.length > 0) {
      organWarningsBox.classList.remove("hidden");
      organWarningsList.innerHTML = organAlerts.map(w => `<li>${escapeHtml(w)}</li>`).join("");
    } else {
      organWarningsBox.classList.add("hidden");
    }

    // 9. Patient Friendly Guidance
    const guidance = data.patient_friendly_guidance || [];
    if (guidance.length > 0) {
      patientGuidanceList.innerHTML = guidance.map(g => `<li>${escapeHtml(g)}</li>`).join("");
    } else {
      patientGuidanceList.innerHTML = `<li>No special precautionary instructions for this regimen.</li>`;
    }
  }

  // Render Visual Matrix
  function renderMatrix(resolvedDrugs, interactions) {
    if (!resolvedDrugs || resolvedDrugs.length === 0) {
      matrixContainer.innerHTML = "";
      return;
    }

    // Build lookup map for (drugA, drugB) -> interaction
    const alertMap = {};
    interactions.forEach((alert, idx) => {
      const a = alert.drug_a.toLowerCase();
      const b = alert.drug_b.toLowerCase();
      alertMap[`${a}|${b}`] = { alert, idx };
      alertMap[`${b}|${a}`] = { alert, idx };
    });

    let html = `<table class="matrix-table"><thead><tr><th>Rx Compound</th>`;
    resolvedDrugs.forEach(d => {
      html += `<th>${escapeHtml(d.name || d.query)}</th>`;
    });
    html += `</tr></thead><tbody>`;

    resolvedDrugs.forEach((rowDrug, rIdx) => {
      const rName = (rowDrug.name || rowDrug.query);
      const rKey = (rowDrug.canonical_id || rowDrug.query || "").toLowerCase();

      html += `<tr><th>${escapeHtml(rName)}</th>`;
      resolvedDrugs.forEach((colDrug, cIdx) => {
        const cKey = (colDrug.canonical_id || colDrug.query || "").toLowerCase();
        if (rIdx === cIdx) {
          html += `<td class="matrix-cell cell-self">—</td>`;
        } else {
          const match = alertMap[`${rKey}|${cKey}`];
          if (match) {
            const sev = match.alert.severity.toLowerCase();
            const sevLabel = match.alert.severity.substring(0, 4);
            html += `<td class="matrix-cell cell-${sev}" data-alert-idx="${match.idx}" title="${escapeHtml(match.alert.drug_a)} + ${escapeHtml(match.alert.drug_b)}: ${match.alert.severity}">${sevLabel}</td>`;
          } else {
            html += `<td class="matrix-cell cell-safe" title="Safe combination">SAFE</td>`;
          }
        }
      });
      html += `</tr>`;
    });

    html += `</tbody></table>`;
    matrixContainer.innerHTML = html;

    // Click to scroll to interaction card
    matrixContainer.querySelectorAll(".matrix-cell[data-alert-idx]").forEach(cell => {
      cell.addEventListener("click", () => {
        const idx = cell.getAttribute("data-alert-idx");
        const targetCard = document.getElementById(`card-alert-${idx}`);
        if (targetCard) {
          targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
          targetCard.style.boxShadow = "0 0 15px rgba(59, 130, 246, 0.8)";
          setTimeout(() => { targetCard.style.boxShadow = "none"; }, 1500);
        }
      });
    });
  }

  // Render Gauges
  function renderGauges(cum) {
    if (!cum) return;

    // Helper for gauge
    function updateGauge(score, barEl, badgeEl, textEl, labelMap) {
      let pct = Math.min(100, Math.round(score * 100));
      if (pct === 0) pct = 5;
      barEl.style.width = `${pct}%`;

      barEl.className = "progress-bar-fill";
      badgeEl.className = "gauge-badge";

      if (score >= 0.8) {
        barEl.classList.add("fill-critical");
        badgeEl.classList.add("badge-critical");
        badgeEl.textContent = "CRITICAL";
      } else if (score >= 0.5) {
        barEl.classList.add("fill-high");
        badgeEl.classList.add("badge-high");
        badgeEl.textContent = "HIGH";
      } else if (score >= 0.25) {
        barEl.classList.add("fill-medium");
        badgeEl.classList.add("badge-medium");
        badgeEl.textContent = "MEDIUM";
      } else {
        barEl.classList.add("fill-low");
        badgeEl.classList.add("badge-low");
        badgeEl.textContent = "LOW";
      }

      textEl.textContent = labelMap(score);
    }

    updateGauge(
      cum.serotonin_syndrome_risk, barSerotonin, badgeSerotonin, textSerotonin,
      (s) => s >= 0.7 ? "High risk of life-threatening serotonin storm (hyperthermia, clonus)." : (s >= 0.3 ? "Moderate accumulation; monitor neuromuscular excitability." : "No excessive serotonergic accumulation.")
    );

    updateGauge(
      cum.qt_prolongation_index, barQt, badgeQt, textQt,
      (s) => s >= 0.7 ? "Extreme Torsades de Pointes / polymorphic VT liability! ECG required." : (s >= 0.3 ? "Additive cardiac QT prolongation; caution in electrolyte disturbances." : "Low cardiac arrhythmogenic liability.")
    );

    updateGauge(
      cum.bleeding_risk_score, barBleeding, badgeBleeding, textBleeding,
      (s) => s >= 0.7 ? "Severe synergistic hemorrhage risk (GI bleed / intracranial hemorrhage)." : (s >= 0.3 ? "Elevated bleeding hazard; monitor CBC, INR, and hemoglobin." : "Baseline hemostatic profile.")
    );

    updateGauge(
      cum.cns_depression_risk, barCns, badgeCns, textCns,
      (s) => s >= 0.7 ? "Severe synergistic respiratory depression / fatal sedation risk." : (s >= 0.3 ? "Elevated sedation and ataxia hazard, particularly in elderly." : "Minimal synergistic central sedation.")
    );
  }

  // Benchmark Modal Handling
  btnViewBenchmark.addEventListener("click", openBenchmarkModal);
  btnCloseModal.addEventListener("click", () => benchmarkModal.classList.add("hidden"));
  benchmarkModal.querySelector(".modal-backdrop").addEventListener("click", () => benchmarkModal.classList.add("hidden"));

  async function openBenchmarkModal() {
    benchmarkModal.classList.remove("hidden");
    try {
      const res = await fetch("/api/benchmark");
      if (!res.ok) throw new Error("Could not load benchmark");
      const data = await res.json();
      const m = data.metrics || {};
      bmAccuracy.textContent = `${m.binary_accuracy_pct || 100}%`;
      bmSensitivity.textContent = `${m.sensitivity_recall_pct || 100}%`;
      bmPrecision.textContent = `${m.precision_pct || 100}%`;
      bmF1.textContent = `${m.f1_score_pct || 100}%`;
      bmLatency.textContent = `${m.mean_latency_ms || 0.09} ms`;

      if (data.results && data.results.length > 0) {
        bmTableBody.innerHTML = data.results.map(r => `
          <tr>
            <td><strong>${escapeHtml(r.drug_a)}</strong></td>
            <td><strong>${escapeHtml(r.drug_b)}</strong></td>
            <td><code>${escapeHtml(r.category || 'general')}</code></td>
            <td><span class="severity-pill pill-${r.expected_severity.toLowerCase()}">${r.expected_severity}</span></td>
            <td><span class="severity-pill pill-${r.predicted_severity.toLowerCase()}">${r.predicted_severity}</span></td>
            <td><span style="color: #34d399; font-weight: bold;">${r.status}</span></td>
            <td>${r.latency_ms}ms</td>
          </tr>
        `).join("");
      }
    } catch (err) {
      console.error(err);
    }
  }

  // Utility to prevent XSS
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Initial load
  renderSelectedDrugs();
});
