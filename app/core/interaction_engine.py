"""
PharmaShield AI - Clinical Interaction & Polypharmacy Risk Engine
Deterministic, mechanistic analysis of drug-drug interactions, cumulative multi-drug toxicity,
CYP450 metabolic competition, Beers Criteria for geriatrics, renal clearance hazards,
and algorithmic recommendation of safer pharmacological alternatives.
"""

from typing import List, Dict, Any, Tuple, Optional
from app.core.schemas import (
    SeverityLevel,
    RiskCategory,
    InteractionAlert,
    CumulativeRiskReport,
    AlternativeRecommendation,
    PatientProfile,
)
from app.core.pharmacology_db import (
    DRUGS_DB,
    CLINICAL_INTERACTIONS_RULES,
    SAFE_ALTERNATIVES_MAP,
)


class ClinicalInteractionEngine:
    """Core interaction and safety evaluation engine."""

    def __init__(self):
        # Index explicit pairwise rules for O(1) bi-directional lookup
        self.rules_lookup: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for rule in CLINICAL_INTERACTIONS_RULES:
            drug_a, drug_b = rule["pair"]
            self.rules_lookup[(drug_a, drug_b)] = rule
            self.rules_lookup[(drug_b, drug_a)] = rule

    def evaluate_regime(
        self,
        drug_ids: List[str],
        patient: PatientProfile
    ) -> Tuple[List[InteractionAlert], CumulativeRiskReport, List[AlternativeRecommendation], List[str], SeverityLevel]:
        """
        Evaluates a complete medication regime for a specific patient profile.
        Returns:
            - List of interaction alerts
            - Cumulative risk report
            - Alternative recommendations
            - Patient-friendly guidance
            - Maximum severity level
        """
        unique_drugs = list(dict.fromkeys(drug_ids))
        interactions: List[InteractionAlert] = []
        seen_pairs = set()

        # 1. Pairwise Interaction Evaluation
        for i in range(len(unique_drugs)):
            for j in range(i + 1, len(unique_drugs)):
                d1 = unique_drugs[i]
                d2 = unique_drugs[j]
                pair_key = tuple(sorted([d1, d2]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                alert = self._evaluate_drug_pair(d1, d2, patient)
                if alert:
                    interactions.append(alert)

        # 2. Cumulative Multi-Drug Polypharmacy Risks
        cumulative_risks = self._compute_cumulative_risks(unique_drugs, patient)

        # 3. Pharmacological Alternative Recommendations
        alternatives = self._generate_alternatives(interactions, unique_drugs)

        # 4. Patient-Friendly Guidance Checklist
        patient_guidance = self._generate_patient_guidance(interactions, cumulative_risks, patient)

        # 5. Determine Overall Maximum Severity
        max_severity = SeverityLevel.SAFE
        if any(alert.severity == SeverityLevel.CONTRAINDICATED for alert in interactions) or cumulative_risks.triple_whammy_nephrotoxicity:
            max_severity = SeverityLevel.CONTRAINDICATED
        elif any(alert.severity == SeverityLevel.SEVERE for alert in interactions) or cumulative_risks.qt_prolongation_status == RiskCategory.CRITICAL or cumulative_risks.serotonin_syndrome_status == RiskCategory.CRITICAL:
            max_severity = SeverityLevel.SEVERE
        elif any(alert.severity == SeverityLevel.MODERATE for alert in interactions):
            max_severity = SeverityLevel.MODERATE
        elif any(alert.severity == SeverityLevel.MINOR for alert in interactions):
            max_severity = SeverityLevel.MINOR

        return interactions, cumulative_risks, alternatives, patient_guidance, max_severity

    def _evaluate_drug_pair(self, d1: str, d2: str, patient: PatientProfile) -> Optional[InteractionAlert]:
        """Evaluates a single pair of drugs against explicit clinical rules and dynamic CYP models."""
        drug1_info = DRUGS_DB.get(d1)
        drug2_info = DRUGS_DB.get(d2)

        if not drug1_info or not drug2_info:
            return None

        # Check explicit curated rules first
        if (d1, d2) in self.rules_lookup:
            rule = self.rules_lookup[(d1, d2)]
            return InteractionAlert(
                drug_a=drug1_info["name"],
                drug_b=drug2_info["name"],
                severity=SeverityLevel(rule["severity"]),
                mechanism_type=rule["mechanism_type"],
                mechanism=rule["mechanism"],
                clinical_effect=rule["clinical_effect"],
                clinical_management=rule["clinical_management"],
                evidence_level=rule["evidence_level"],
                evidence_citations=rule.get("citations", [])
            )

        # Dynamic CYP450 Inhibition & Substrate Conflict Detection
        cyp_inhibitors_1 = set(drug1_info.get("cyp_inhibitors", []))
        cyp_substrates_2 = set(drug2_info.get("cyp_substrates", []))
        overlap_1_2 = cyp_inhibitors_1.intersection(cyp_substrates_2)

        cyp_inhibitors_2 = set(drug2_info.get("cyp_inhibitors", []))
        cyp_substrates_1 = set(drug1_info.get("cyp_substrates", []))
        overlap_2_1 = cyp_inhibitors_2.intersection(cyp_substrates_1)

        if overlap_1_2 or overlap_2_1:
            inhibitor = drug1_info["name"] if overlap_1_2 else drug2_info["name"]
            substrate = drug2_info["name"] if overlap_1_2 else drug1_info["name"]
            shared_cyps = list(overlap_1_2 if overlap_1_2 else overlap_2_1)
            cyp_str = ", ".join(shared_cyps)

            return InteractionAlert(
                drug_a=drug1_info["name"],
                drug_b=drug2_info["name"],
                severity=SeverityLevel.MODERATE,
                mechanism_type=f"Pharmacokinetic (CYP450 Enzyme Inhibition: {cyp_str})",
                mechanism=f"{inhibitor} inhibits {cyp_str}, which is a major metabolic clearance pathway for {substrate}.",
                clinical_effect=f"Elevated plasma concentrations and prolonged half-life of {substrate}, increasing adverse reaction frequency.",
                clinical_management=f"Monitor patient closely for {substrate} adverse effects or consider dosage reduction.",
                evidence_level="Established Pharmacokinetic Pathway",
                evidence_citations=["Goodman & Gilman's Pharmacological Basis of Therapeutics (14th Ed)"]
            )

        return None

    def _compute_cumulative_risks(self, drug_ids: List[str], patient: PatientProfile) -> CumulativeRiskReport:
        """Calculates multi-drug polypharmacy risk indices."""
        serotonin_drugs = []
        serotonin_score = 0.0

        qt_drugs = []
        qt_score = 0.0

        bleeding_drugs = []
        bleeding_score = 0.0

        cns_drugs = []
        cns_score = 0.0

        nephrotoxic_factors: Dict[str, List[str]] = {"ACEI": [], "DIURETIC": [], "NSAID": []}
        beers_flags = []
        organ_warnings = []

        for did in drug_ids:
            info = DRUGS_DB.get(did)
            if not info:
                continue

            name = info["name"]

            # Serotonin
            s_val = info.get("serotonergic_score", 0.0)
            if s_val > 0.0:
                serotonin_score += s_val
                serotonin_drugs.append(f"{name} ({info['class']})")

            # QT prolongation
            qt_level = info.get("qt_risk", "NONE")
            if qt_level == "HIGH":
                qt_score += 0.50
                qt_drugs.append(f"{name} [High Arrhythmogenic Risk]")
            elif qt_level == "MODERATE":
                qt_score += 0.25
                qt_drugs.append(f"{name} [Moderate QT Risk]")
            elif qt_level == "LOW":
                qt_score += 0.10

            # Bleeding
            b_val = info.get("bleeding_score", 0.0)
            if b_val > 0.0:
                bleeding_score += b_val
                bleeding_drugs.append(f"{name} [Bleeding Factor: {b_val}]")

            # CNS Depression
            c_val = info.get("cns_depression_score", 0.0)
            if c_val > 0.0:
                cns_score += c_val
                cns_drugs.append(f"{name} [Sedation Factor: {c_val}]")

            # Triple Whammy
            n_type = info.get("nephrotoxic_type")
            if n_type in nephrotoxic_factors:
                nephrotoxic_factors[n_type].append(name)

            # Beers Criteria (Age >= 65)
            if patient.age >= 65 and info.get("beers_criteria"):
                beers_flags.append(f"⚠️ {name}: {info.get('beers_rationale')}")

            # Organ Clearance Checks
            renal_pct = info.get("renal_clearance_pct", 0.0)
            if patient.eGFR is not None and patient.eGFR < 30.0 and renal_pct >= 50.0:
                organ_warnings.append(
                    f"🛑 Renal Impairment Alert: {name} undergoes {renal_pct:.0f}% renal elimination. "
                    f"Patient eGFR ({patient.eGFR} mL/min) presents severe drug accumulation and toxicity hazard. Mandatory dose reduction or alternative required."
                )
            elif patient.eGFR is not None and patient.eGFR < 60.0 and renal_pct >= 75.0:
                organ_warnings.append(
                    f"⚠️ Renal Caution: {name} ({renal_pct:.0f}% renal clearance). Monitor renal function and adjust dose for eGFR {patient.eGFR} mL/min."
                )

            # Hepatic Impairment Check
            hepatic_pct = info.get("hepatic_clearance_pct", 0.0)
            if patient.hepatic_impairment and hepatic_pct >= 80.0:
                organ_warnings.append(
                    f"⚠️ Hepatic Clearance Warning: {name} relies on {hepatic_pct:.0f}% liver metabolism. "
                    f"Use with caution in hepatic dysfunction; serum drug monitoring recommended."
                )

            # Pregnancy category
            preg_cat = info.get("pregnancy_category", "C")
            if patient.is_pregnant and preg_cat in ["D", "X"]:
                organ_warnings.append(
                    f"🛑 Teratogenicity Alert: {name} is FDA Pregnancy Category {preg_cat}. "
                    f"Proven risk of fetal skeletal malformations or fetal demise. Contraindicated in pregnancy."
                )

        # Normalize score caps to [0.0, 1.0]
        norm_serotonin = min(1.0, round(serotonin_score / 1.8, 3))
        norm_qt = min(1.0, round(qt_score, 3))
        norm_bleeding = min(1.0, round(bleeding_score / 1.6, 3))
        norm_cns = min(1.0, round(cns_score / 1.7, 3))

        # Classify status categories
        s_status = RiskCategory.LOW
        if norm_serotonin >= 0.80 or len(serotonin_drugs) >= 3:
            s_status = RiskCategory.CRITICAL
        elif norm_serotonin >= 0.50 or len(serotonin_drugs) >= 2:
            s_status = RiskCategory.HIGH
        elif norm_serotonin >= 0.25:
            s_status = RiskCategory.ELEVATED

        qt_status = RiskCategory.LOW
        if norm_qt >= 0.80 or len([d for d in qt_drugs if "High" in d]) >= 2:
            qt_status = RiskCategory.CRITICAL
        elif norm_qt >= 0.50:
            qt_status = RiskCategory.HIGH
        elif norm_qt >= 0.20:
            qt_status = RiskCategory.ELEVATED

        b_status = RiskCategory.LOW
        if norm_bleeding >= 0.80 or len(bleeding_drugs) >= 3:
            b_status = RiskCategory.CRITICAL
        elif norm_bleeding >= 0.50 or len(bleeding_drugs) >= 2:
            b_status = RiskCategory.HIGH
        elif norm_bleeding >= 0.20:
            b_status = RiskCategory.ELEVATED

        cns_status = RiskCategory.LOW
        if norm_cns >= 0.80:
            cns_status = RiskCategory.CRITICAL
        elif norm_cns >= 0.50:
            cns_status = RiskCategory.HIGH
        elif norm_cns >= 0.25:
            cns_status = RiskCategory.ELEVATED

        # Triple Whammy check
        triple_whammy = bool(
            nephrotoxic_factors["ACEI"]
            and nephrotoxic_factors["DIURETIC"]
            and nephrotoxic_factors["NSAID"]
        )
        triple_drugs = []
        if triple_whammy:
            triple_drugs = (
                nephrotoxic_factors["ACEI"]
                + nephrotoxic_factors["DIURETIC"]
                + nephrotoxic_factors["NSAID"]
            )
            organ_warnings.append(
                f"🛑 Triple Whammy Acute Kidney Injury Alert: Concomitant {', '.join(triple_drugs)} combines efferent arteriole dilation, afferent arteriole constriction, and hypovolemia, drastically increasing acute renal failure risk."
            )

        return CumulativeRiskReport(
            serotonin_syndrome_risk=norm_serotonin,
            serotonin_syndrome_status=s_status,
            serotonin_contributing_drugs=serotonin_drugs,
            qt_prolongation_index=norm_qt,
            qt_prolongation_status=qt_status,
            qt_contributing_drugs=qt_drugs,
            bleeding_risk_score=norm_bleeding,
            bleeding_risk_status=b_status,
            bleeding_contributing_drugs=bleeding_drugs,
            triple_whammy_nephrotoxicity=triple_whammy,
            triple_whammy_drugs=triple_drugs,
            cns_depression_risk=norm_cns,
            cns_depression_status=cns_status,
            cns_contributing_drugs=cns_drugs,
            beers_criteria_flags=beers_flags,
            organ_clearance_warnings=organ_warnings,
        )

    def _generate_alternatives(
        self,
        interactions: List[InteractionAlert],
        drug_ids: List[str]
    ) -> List[AlternativeRecommendation]:
        """Generates evidence-based safer drug alternatives for identified high-risk interactions."""
        recs = []
        seen = set()

        for alert in interactions:
            if alert.severity in [SeverityLevel.CONTRAINDICATED, SeverityLevel.SEVERE]:
                for did in drug_ids:
                    info = DRUGS_DB.get(did)
                    if not info:
                        continue
                    name = info["name"]
                    if (name == alert.drug_a or name == alert.drug_b) and did in SAFE_ALTERNATIVES_MAP:
                        if did not in seen:
                            seen.add(did)
                            alt_data = SAFE_ALTERNATIVES_MAP[did]
                            recs.append(
                                AlternativeRecommendation(
                                    problematic_drug=name,
                                    suggested_alternative=alt_data["suggested"],
                                    therapeutic_class=alt_data["therapeutic_class"],
                                    rationale=alt_data["rationale"],
                                    safety_advantage=alt_data["safety_advantage"],
                                )
                            )
        return recs

    def _generate_patient_guidance(
        self,
        interactions: List[InteractionAlert],
        cumulative: CumulativeRiskReport,
        patient: PatientProfile
    ) -> List[str]:
        """Generates clear, patient-friendly guidance and warning signs."""
        guidance = []

        if cumulative.serotonin_syndrome_status in [RiskCategory.CRITICAL, RiskCategory.HIGH]:
            guidance.append(
                "🚨 Serotonin Warning: Watch for shivering, muscle twitches or stiffness, fever, rapid heartbeat, and extreme agitation. Seek emergency care immediately if these occur."
            )

        if cumulative.qt_prolongation_status in [RiskCategory.CRITICAL, RiskCategory.HIGH]:
            guidance.append(
                "💓 Heart Rhythm Warning: Report sudden fluttering in your chest, fainting spells, unexplained dizziness, or shortness of breath to your healthcare team right away."
            )

        if cumulative.bleeding_risk_status in [RiskCategory.CRITICAL, RiskCategory.HIGH]:
            guidance.append(
                "🩸 Bleeding Precautions: Avoid contact sports, use a soft-bristled toothbrush, and look out for unusual bruising, black or tarry stools, or nosebleeds that do not stop."
            )

        if cumulative.triple_whammy_nephrotoxicity:
            guidance.append(
                "💧 Kidney Alert (Triple Whammy): Taking blood pressure pills, water pills, and pain relievers (NSAIDs) together can stress your kidneys. Stay hydrated and avoid over-the-counter ibuprofen or naproxen."
            )

        if cumulative.cns_depression_status in [RiskCategory.CRITICAL, RiskCategory.HIGH]:
            guidance.append(
                "⚠️ Drowsiness Caution: Do not drive or operate heavy machinery. Concomitant sedatives/pain medications drastically slow reaction times and breathing."
            )

        if patient.age >= 65 and cumulative.beers_criteria_flags:
            guidance.append(
                "👴 Senior Care Notice: Certain medications in your list are associated with higher fall risks or confusion in adults over 65. Consult your pharmacist for dose titration."
            )

        if not guidance:
            guidance.append("✅ No major polypharmacy danger signs detected. Take all medications exactly as directed by your prescribing physician.")

        return guidance
