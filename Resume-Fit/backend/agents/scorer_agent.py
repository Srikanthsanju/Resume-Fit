"""
Strict ATS + Resume Realism Scorer

Designed to work with the paired writer agent and guidelines.
Key features:
- scores evidence, realism, and recruiter trust not just keywords
- treats Fulltime and Contract differently
- allows granular skills to remain in Skills
- does not over-penalize replaceable skills in Fulltime mode
- generates writer-ready feedback with rewrite examples
- excludes rulebook-approved differences such as summary length and date mode
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI


class ScorerAgent:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        # High-reasoning default. Override with OPENAI_MODEL if needed.
        self.model = os.getenv("OPENAI_MODEL", "gpt-5-pro")

        config_dir = Path(__file__).parent.parent / "config"
        self.guidelines = ""
        guidelines_path = config_dir / "guidelines.md"
        if guidelines_path.exists():
            self.guidelines = guidelines_path.read_text(encoding="utf-8")

        self.generic_phrases = {
            "proven track record", "demonstrated ability", "deep expertise",
            "strong experience", "hands-on experience", "expertise in",
            "cutting-edge", "best-in-class", "world-class", "robust solutions",
            "delivering business value"
        }

        self.replaceable_terms = {
            "java", "crewai", "pydantic", "tensorflow", "computer vision", "recommender systems"
        }

        self.granular_skill_terms = {
            "glue", "ecr", "iam", "vpc", "athena", "redshift", "lambda", "emr",
            "cloudwatch", "bedrock", "step functions", "fastapi", "llamaindex",
            "redis", "postgresql", "snowflake", "bigquery", "encryption"
        }

        self.core_capability_terms = {
            "python", "sql", "aws", "azure", "sagemaker", "sagemaker pipelines",
            "model registry", "experiment tracking", "hyperparameter tuning", "batch inference",
            "managed endpoints", "docker", "kubernetes", "mlops", "ci/cd", "monitoring",
            "retraining", "feature engineering", "pytorch", "scikit-learn", "xgboost",
            "openai", "llm", "rag", "langchain", "langgraph", "documentation",
            "agile", "governance", "architecture", "vector databases", "embeddings"
        }

        self.workflow_terms = {
            "data_objects": [
                "call transcript", "policy document", "resume", "job listing", "training dataset",
                "feature table", "vector index", "model artifact", "endpoint", "batch job",
                "api request", "document corpus", "customer profile", "warehouse table"
            ],
            "ops": [
                "monitoring", "drift", "alert", "retry", "rollback", "autoscaling",
                "latency", "throughput", "endpoint", "batch inference", "real-time"
            ],
            "training": [
                "training", "evaluation", "cross-validation", "hyperparameter", "registry",
                "retraining", "fine-tuned", "lora", "qlora"
            ],
            "architecture": [
                "review", "guardrail", "blueprint", "reference architecture", "technical design",
                "integration pattern", "orchestration", "data flow", "vendor evaluation", "roadmap"
            ]
        }

    def score_resume(self, job_description: str, resume_content: dict, job_type: str = "Fulltime") -> dict:
        resume_text = self._format_resume_for_review(resume_content)
        structured_resume = self._extract_resume_structure(resume_content)
        jd_signals = self._extract_jd_signals(job_description)
        heuristic = self._heuristic_analysis(structured_resume, jd_signals, job_type)

        schema = {
            "score": 0,
            "passed": False,
            "ats_confidence": "low|medium|high",
            "recruiter_confidence": "low|medium|high",
            "breakdown": {
                "must_have_evidence": {"score": 0, "max": 25, "details": ""},
                "experience_alignment": {"score": 0, "max": 20, "details": ""},
                "wording_realism": {"score": 0, "max": 15, "details": ""},
                "skills_credibility": {"score": 0, "max": 15, "details": ""},
                "domain_coherence": {"score": 0, "max": 10, "details": ""},
                "impact_specificity": {"score": 0, "max": 10, "details": ""},
                "format_clarity": {"score": 0, "max": 5, "details": ""}
            },
            "evidence_strength": {"strong": [], "medium": [], "weak_or_missing": []},
            "forced_or_generic_signals": [],
            "skill_gaps": [],
            "wording_gaps": [],
            "top_fixes": [],
            "strengths": [],
            "writer_feedback": {
                "core_ownership_areas": [],
                "skills_to_emphasize": [],
                "skills_ok_in_skills_only": [],
                "bad_patterns_to_avoid": [],
                "rewrite_examples": [],
                "summary_guidance": ""
            }
        }

        system_prompt = f"""
You are a strict ATS and recruiter-quality resume evaluator.

Job type: {job_type}

You must score realistically, not generously.
Important rules:
- score evidence inside work bullets more than summary or skills
- do not over-penalize rulebook-approved differences such as summary length, date mode, or selective emphasis of replaceable skills
- in Fulltime mode, be stricter about realism and inflated wording
- in Contract mode, allow broader keyword mirroring if still believable
- granular tools may stay only in Skills without heavy penalty
- replaceable skills such as Java vs Python or CrewAI vs LangChain do not need equal emphasis in Fulltime mode
- penalize inflated architect claims if work bullets do not support them
- separate ATS fit from recruiter trust
- produce writer-ready feedback with concrete rewrite examples

Return only valid JSON matching this schema:
{json.dumps(schema, indent=2)}
"""

        user_prompt = f"""
JOB DESCRIPTION
{job_description}

RESUME TEXT
{resume_text}

HEURISTIC ANALYSIS
{json.dumps(heuristic, indent=2)}

Evaluate strictly but fairly.
Do not score down for rulebook-approved differences.
Give concrete rewrite suggestions the writer can use in the next iteration.
Return only JSON.
"""

        response = self.client.responses.create(
            model=self.model,
            reasoning={"effort": "high"},
            text={"format": {"type": "text"}},
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = getattr(response, "output_text", "") or ""
        try:
            result = json.loads(content.strip())
        except Exception:
            result = {
                "score": 0,
                "passed": False,
                "ats_confidence": "low",
                "recruiter_confidence": "low",
                "breakdown": {},
                "evidence_strength": {"strong": [], "medium": [], "weak_or_missing": []},
                "forced_or_generic_signals": ["Failed to parse model output."],
                "skill_gaps": [],
                "wording_gaps": ["Scorer response parse failure"],
                "top_fixes": ["Retry scorer request"],
                "strengths": [],
                "writer_feedback": {
                    "core_ownership_areas": [],
                    "skills_to_emphasize": [],
                    "skills_ok_in_skills_only": [],
                    "bad_patterns_to_avoid": [],
                    "rewrite_examples": [],
                    "summary_guidance": ""
                }
            }

        result = self._apply_post_adjustments(result, heuristic, jd_signals, job_type)
        result["writer_feedback"] = self._build_writer_feedback(result, heuristic, jd_signals, job_type)
        return result

    def _format_resume_for_review(self, resume_content: dict) -> str:
        lines: List[str] = []
        if "summary" in resume_content:
            lines.append("## SUMMARY")
            for item in resume_content["summary"]:
                lines.append(f"- {item}")
        if "skills" in resume_content:
            lines.append("\n## TECHNICAL SKILLS")
            for category, skills in resume_content["skills"].items():
                lines.append(f"{category}: {skills}")
        mapping = {
            "bee_data": "## BEE DATA TECHNOLOGIES",
            "allied_health": "## ALLIED HEALTH AGENCY",
            "byjus": "## BYJU'S",
            "cognizant": "## COGNIZANT",
        }
        for key, header in mapping.items():
            if key in resume_content:
                lines.append(f"\n{header}")
                for item in resume_content[key]:
                    lines.append(f"- {item}")
        return "\n".join(lines)

    def _extract_resume_structure(self, resume_content: dict) -> dict:
        return {
            "summary": resume_content.get("summary", []),
            "skills": resume_content.get("skills", {}),
            "experience": {
                k: resume_content.get(k, [])
                for k in ["bee_data", "allied_health", "byjus", "cognizant"]
            }
        }

    def _extract_jd_signals(self, job_description: str) -> dict:
        jd_lower = job_description.lower()
        candidates = [
            "python", "java", "aws", "azure", "sagemaker", "docker", "kubernetes",
            "langchain", "crewai", "pydantic", "llm", "rag", "vector databases",
            "embeddings", "monitoring", "retraining", "documentation", "agile",
            "governance", "architecture", "reference architecture", "pi planning",
            "art", "architectural runway", "vendor evaluation", "model registry",
            "experiment tracking", "feature engineering", "computer vision", "recommender systems"
        ]
        explicit = [c for c in candidates if c in jd_lower]
        return {"raw": job_description, "explicit": explicit}

    def _heuristic_analysis(self, structured_resume: dict, jd_signals: dict, job_type: str) -> dict:
        summary_text = " ".join(structured_resume["summary"]).lower()
        skills_text = " ".join(f"{k} {v}" for k, v in structured_resume["skills"].items()).lower()
        bullets = [b for section in structured_resume["experience"].values() for b in section]
        bullets_text = " ".join(bullets).lower()

        evidence = {"strong": [], "medium": [], "weak_or_missing": []}
        unsupported_core = []
        for term in jd_signals["explicit"]:
            exp_hits = sum(1 for b in bullets if term in b.lower())
            in_summary = term in summary_text
            in_skills = term in skills_text
            if exp_hits >= 2:
                evidence["strong"].append(term)
            elif exp_hits == 1:
                evidence["medium"].append(term)
            else:
                evidence["weak_or_missing"].append(term)
                if term in self.core_capability_terms and not (
                    job_type.lower() == "fulltime" and term in self.replaceable_terms
                ):
                    if not (in_summary or in_skills):
                        unsupported_core.append(term)

        generic_hits = [p for p in self.generic_phrases if p in (summary_text + " " + bullets_text)]
        repetitive_starts = self._repetitive_starts(bullets)
        vague_bullets = [b for b in bullets if self._is_vague_bullet(b)]
        overloaded_bullets = [b for b in bullets if self._is_overloaded_bullet(b)]
        realistic_bullets = [b for b in bullets if self._is_grounded_bullet(b)]
        metrics_ratio = self._metrics_ratio(bullets)
        role_scope = self._role_scope(structured_resume["experience"])

        return {
            "evidence": evidence,
            "unsupported_core": unsupported_core,
            "generic_hits": generic_hits,
            "repetitive_starts": repetitive_starts,
            "vague_bullets": vague_bullets[:8],
            "overloaded_bullets": overloaded_bullets[:8],
            "realistic_bullets": realistic_bullets[:8],
            "metrics_ratio": metrics_ratio,
            "role_scope": role_scope,
            "job_type": job_type,
        }

    def _repetitive_starts(self, bullets: List[str]) -> Dict[str, int]:
        counts = Counter()
        for bullet in bullets:
            words = bullet.strip().split()
            if words:
                counts[words[0].lower()] += 1
        return {k: v for k, v in counts.items() if v >= 3}

    def _is_vague_bullet(self, bullet: str) -> bool:
        lower = bullet.lower()
        weak_patterns = [
            "worked on", "worked with", "responsible for", "helped with",
            "strong experience", "demonstrated ability"
        ]
        has_weak = any(p in lower for p in weak_patterns)
        has_object = any(x in lower for group in self.workflow_terms.values() for x in group)
        has_metric = bool(re.search(r"\d+%|\d[\d,]*\+?|\bms\b|\busers\b|\brequests\b", lower))
        return has_weak and not has_object and not has_metric

    def _is_overloaded_bullet(self, bullet: str) -> bool:
        lower = bullet.lower()
        tool_count = len(re.findall(r"\b(aws|azure|sagemaker|docker|kubernetes|langchain|openai|pytorch|tensorflow|spark|sql|java|crewai|pydantic)\b", lower))
        has_metric = bool(re.search(r"\d+%|\d[\d,]*\+?", lower))
        has_object = any(x in lower for x in self.workflow_terms["data_objects"])
        return tool_count >= 4 and not has_metric and not has_object

    def _is_grounded_bullet(self, bullet: str) -> bool:
        lower = bullet.lower()
        has_object = any(x in lower for x in self.workflow_terms["data_objects"])
        has_system = bool(re.search(r"\b(aws|azure|sagemaker|docker|kubernetes|endpoint|batch inference|api|langchain|vector)\b", lower))
        has_result = bool(re.search(r"\d+%|\d[\d,]*\+?|\bimprov|\breduc|\bincreas|\bmaintain|\bsupport|\bserve|\benable", lower))
        return has_object and has_system and has_result

    def _metrics_ratio(self, bullets: List[str]) -> float:
        if not bullets:
            return 0.0
        metric_count = sum(1 for b in bullets if re.search(r"\d+%|\d[\d,]*\+?|\bms\b|\busers\b|\brequests\b", b.lower()))
        return round(metric_count / len(bullets), 2)

    def _role_scope(self, experience: Dict[str, List[str]]) -> Dict[str, Any]:
        result = {}
        domain_map = {
            "ml_platform": ["sagemaker", "registry", "endpoint", "monitoring", "retraining"],
            "llm_apps": ["openai", "rag", "langchain", "vector", "prompt"],
            "backend": ["api", "fastapi", "oauth", "service", "java"],
            "data": ["spark", "etl", "warehouse", "feature engineering", "data pipeline"],
            "architecture": ["architecture", "blueprint", "guardrail", "review", "roadmap", "vendor"],
        }
        for role, bullets in experience.items():
            text = " ".join(bullets).lower()
            active = []
            for domain, kws in domain_map.items():
                if sum(1 for kw in kws if kw in text) >= 2:
                    active.append(domain)
            result[role] = {"active_domains": active, "too_broad": len(active) >= 4}
        return result

    def _apply_post_adjustments(self, result: dict, heuristic: dict, jd_signals: dict, job_type: str) -> dict:
        score = int(result.get("score", 0))
        score -= min(len(heuristic["generic_hits"]) * (3 if job_type.lower() == "fulltime" else 2), 10)
        score -= min(len(heuristic["vague_bullets"]) * 2, 8)
        score -= min(len(heuristic["overloaded_bullets"]) * 2, 8)
        if heuristic["metrics_ratio"] < 0.2:
            score -= 3 if job_type.lower() == "fulltime" else 1
        if len(heuristic["unsupported_core"]) >= 5:
            score = min(score, 84 if job_type.lower() == "fulltime" else 88)

        recruiter_conf = result.get("recruiter_confidence", "medium")
        if heuristic["vague_bullets"] or heuristic["overloaded_bullets"]:
            recruiter_conf = "low" if recruiter_conf != "high" else "medium"
        elif heuristic["realistic_bullets"]:
            recruiter_conf = "medium" if recruiter_conf == "low" else recruiter_conf

        forced = result.get("forced_or_generic_signals", [])
        forced += [f"Generic phrase used: {x}" for x in heuristic["generic_hits"][:6]]
        forced += [f"Vague bullet: {x}" for x in heuristic["vague_bullets"][:3]]
        forced += [f"Overloaded bullet: {x}" for x in heuristic["overloaded_bullets"][:3]]
        result["forced_or_generic_signals"] = forced[:12]

        wording_gaps = result.get("wording_gaps", [])
        if heuristic["repetitive_starts"]:
            wording_gaps.append(
                "Repeated bullet openings reduce natural tone: " + ", ".join(f"{k} ({v}x)" for k, v in heuristic["repetitive_starts"].items())
            )
        if heuristic["vague_bullets"]:
            wording_gaps.append("Some bullets need a clearer object, operational step, or result.")
        if heuristic["overloaded_bullets"]:
            wording_gaps.append("Some bullets contain too many tools without enough grounding.")
        result["wording_gaps"] = wording_gaps[:10]

        skill_gaps = result.get("skill_gaps", [])
        for skill in heuristic["unsupported_core"][:8]:
            skill_gaps.append(f"Core skill not clearly supported by work history: {skill}")
        result["skill_gaps"] = skill_gaps[:12]

        result["evidence_strength"] = heuristic["evidence"]
        result["recruiter_confidence"] = recruiter_conf
        result["score"] = max(0, min(score, 100))
        result["passed"] = result["score"] >= 85
        return result

    def _build_writer_feedback(self, result: dict, heuristic: dict, jd_signals: dict, job_type: str) -> dict:
        core_areas = self._infer_ownership_areas(jd_signals["explicit"])
        emphasize = [x for x in jd_signals["explicit"] if x not in self.granular_skill_terms and not (job_type.lower() == "fulltime" and x in self.replaceable_terms)][:10]
        skills_only = [x for x in jd_signals["explicit"] if x in self.granular_skill_terms or (job_type.lower() == "fulltime" and x in self.replaceable_terms)][:10]

        bad_patterns = [
            "Do not write summary bullets like pasted JD lines.",
            "Do not use proven track record, demonstrated ability, deep expertise, or strong experience.",
            "Do not stack 4 or more tools in a bullet unless the workflow truly requires it.",
            "Do not claim enterprise architecture or governance ownership beyond what the work history supports.",
            "Do not force defense, clearance, or national-security positioning unless extensively proven.",
        ]

        rewrites = [
            {
                "bad": "Worked on SageMaker, Docker, Kubernetes, and MLflow for model deployment.",
                "better": "Built SageMaker deployment workflows for batch and real-time inference, packaged services in Docker, and tracked model versions in MLflow to support controlled releases."
            },
            {
                "bad": "Strong experience with machine learning and large language models.",
                "better": "Built production ML workflows and LLM-based retrieval services used in customer support and document search flows."
            },
            {
                "bad": "Responsible for model monitoring and retraining.",
                "better": "Implemented monitoring for prediction drift and response quality, then triggered retraining jobs when service thresholds were breached."
            },
            {
                "bad": "Used LangChain and OpenAI for RAG.",
                "better": "Developed a RAG workflow that retrieved policy content from a vector index and injected grounded context into GPT responses for support teams."
            },
            {
                "bad": "Designed enterprise AI architecture strategy and standards.",
                "better": "Provided solution-level AI design guidance for integration patterns, model lifecycle decisions, and review checkpoints across delivery teams."
            },
        ]

        summary_guidance = (
            "Write summary with about 60% role and JD alignment and 40% systems, production actions, or business context. "
            "Keep it metric-free. Do not force domain branding. Prefer grounded identity statements over claim-heavy phrases."
        )

        top_fixes = result.get("top_fixes", [])
        if heuristic["vague_bullets"]:
            top_fixes.append("Replace vague bullets with object + action + system + result wording.")
        if heuristic["overloaded_bullets"]:
            top_fixes.append("Split overloaded bullets so each one focuses on one workflow and one outcome.")
        if heuristic["unsupported_core"]:
            top_fixes.append("Emphasize core JD capabilities in work bullets, while leaving replaceable or granular items in Skills if needed.")
        if any(v.get("too_broad") for v in heuristic["role_scope"].values()) and job_type.lower() == "fulltime":
            top_fixes.append("Reduce breadth in at least one role so the profile feels focused rather than inflated.")
        result["top_fixes"] = top_fixes[:10]

        strengths = result.get("strengths", [])
        if heuristic["realistic_bullets"]:
            strengths.append("Some bullets already sound grounded and operational rather than keyword-driven.")
        result["strengths"] = strengths[:8]

        return {
            "core_ownership_areas": core_areas,
            "skills_to_emphasize": emphasize,
            "skills_ok_in_skills_only": skills_only,
            "bad_patterns_to_avoid": bad_patterns,
            "rewrite_examples": rewrites,
            "summary_guidance": summary_guidance,
        }

    def _infer_ownership_areas(self, explicit_terms: List[str]) -> List[str]:
        terms = set(explicit_terms)
        areas = []
        if {"sagemaker", "model registry", "batch inference", "monitoring", "retraining"} & terms:
            areas.append("model lifecycle and inference workflows")
        if {"feature engineering", "aws", "azure"} & terms:
            areas.append("data ingestion and feature engineering pipelines")
        if {"openai", "llm", "rag", "langchain", "langgraph", "crewai"} & terms:
            areas.append("llm application and orchestration workflows")
        if {"docker", "kubernetes"} & terms:
            areas.append("containerized deployment and runtime operations")
        if {"governance", "architecture", "reference architecture", "vendor evaluation"} & terms:
            areas.append("solution architecture, standards, and review guidance")
        if {"documentation", "agile", "pi planning", "architectural runway"} & terms:
            areas.append("delivery planning, documentation, and cross-team alignment")
        return areas[:7]

    def get_improvement_summary(self, score_result: dict) -> str:
        parts = [
            f"STRICT ATS SCORE: {score_result.get('score', 0)}/100",
            f"ATS CONFIDENCE: {score_result.get('ats_confidence', 'unknown')}",
            f"RECRUITER CONFIDENCE: {score_result.get('recruiter_confidence', 'unknown')}",
        ]
        if score_result.get("top_fixes"):
            parts.append("TOP FIXES:")
            for i, item in enumerate(score_result["top_fixes"][:8], 1):
                parts.append(f"  {i}. {item}")
        wf = score_result.get("writer_feedback", {})
        if wf:
            parts.append("WRITER FEEDBACK:")
            if wf.get("core_ownership_areas"):
                parts.append("  Ownership areas: " + ", ".join(wf["core_ownership_areas"]))
            if wf.get("skills_to_emphasize"):
                parts.append("  Emphasize: " + ", ".join(wf["skills_to_emphasize"]))
            if wf.get("skills_ok_in_skills_only"):
                parts.append("  Skills-only is okay for: " + ", ".join(wf["skills_ok_in_skills_only"]))
        return "\n".join(parts)
