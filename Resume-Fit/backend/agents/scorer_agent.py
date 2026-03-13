"""
scorer_agent.py

Strict ATS + recruiter-trust scorer.
Uses OpenAI GPT-5 via Responses API.
Produces writer-ready feedback with concrete rewrites and emphasis guidance.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI


class ScorerAgent:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is missing.")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5")

        config_dir = Path(__file__).parent.parent / "config"
        self.guidelines = ""
        guidelines_path = config_dir / "guidelines.md"
        if guidelines_path.exists():
            self.guidelines = guidelines_path.read_text(encoding="utf-8")

        self.generic_phrases = {
            "proven track record",
            "demonstrated ability",
            "deep expertise",
            "strong experience",
            "hands-on experience",
            "expertise in",
            "cutting-edge",
            "best-in-class",
            "world-class",
            "robust solutions",
            "delivering business value",
        }

        self.replaceable_terms = {
            "java", "crewai", "pydantic", "tensorflow", "computer vision", "recommender systems"
        }

        self.granular_skill_terms = {
            "glue", "ecr", "iam", "vpc", "athena", "redshift", "lambda", "emr",
            "cloudwatch", "bedrock", "step functions", "fastapi", "llamaindex",
            "redis", "postgresql", "snowflake", "bigquery", "encryption",
            "access controls", "service bus", "cosmos db"
        }

        self.core_capability_terms = {
            "python", "sql", "aws", "azure", "sagemaker", "sagemaker pipelines",
            "model registry", "experiment tracking", "hyperparameter tuning", "batch inference",
            "managed endpoints", "docker", "kubernetes", "mlops", "ci/cd", "monitoring",
            "retraining", "feature engineering", "pytorch", "scikit-learn", "xgboost",
            "openai", "llm", "rag", "langchain", "langgraph", "documentation",
            "agile", "governance", "architecture", "vector databases", "embeddings",
            "responsible ai", "explainability", "mentor", "mentoring", "api", "orchestration"
        }

        self.data_object_terms = [
            "call transcript", "policy document", "resume", "job listing", "training dataset",
            "feature table", "vector index", "model artifact", "endpoint", "batch job",
            "api request", "document corpus", "customer profile", "warehouse table",
            "contract", "ticket", "invoice", "knowledge base", "document archive", "sales record"
        ]

    def score_resume(self, job_description: str, resume_content: dict, job_type: str = "Fulltime") -> dict:
        resume_content = self._normalize_resume_content(resume_content)
        resume_text = self._format_resume_for_review(resume_content)
        structured_resume = self._extract_resume_structure(resume_content)
        jd_signals = self._extract_jd_signals(job_description)
        heuristic = self._heuristic_analysis(structured_resume, jd_signals, job_type)

        system_prompt = f"""
You are a strict ATS and recruiter-trust evaluator for technical resumes.

Your job is not just to count keywords.
You must evaluate:
1. ATS keyword alignment
2. believable work evidence
3. wording realism
4. skill credibility
5. role fit vs over-claiming
6. whether the writer can improve the resume on the next pass

Job type: {job_type}

Important scoring rules:
- Evidence in experience bullets matters more than summary and skills.
- Do not over-penalize rulebook-approved differences such as summary length, date mode, or selective emphasis of replaceable skills.
- In Fulltime mode, be stricter about realism, inflated architect language, and forced JD mirroring.
- In Contract mode, allow broader keyword mirroring if still believable.
- Granular tools can stay only in Skills without heavy penalty.
- Replaceable skills such as Java vs Python or CrewAI vs LangChain do not need equal emphasis in Fulltime mode.
- If a skill is optional, adjacent, or replaceable, do not treat it as a hard miss when another stronger substitute is clearly evidenced.
- Do not score down because the resume does not prove every optional tool in work bullets.
- Distinguish ATS fit from recruiter confidence.

Return ONLY valid JSON with this exact shape:
{json.dumps(self._default_result(), indent=2)}
"""

        user_prompt = f"""
JOB DESCRIPTION
{job_description}

RESUME TEXT
{resume_text}

HEURISTIC ANALYSIS
{json.dumps(heuristic, indent=2)}

Evaluate strictly but fairly.
Give concrete feedback the writer can directly use in the next iteration.
Return only JSON.
"""

        raw_text = self._call_model(system_prompt, user_prompt)
        result = self._parse_result(raw_text)
        result = self._normalize_result(result)
        result = self._apply_post_adjustments(result, heuristic, jd_signals, job_type)
        result["writer_feedback"] = self._build_writer_feedback(result, heuristic, jd_signals, job_type)
        return self._normalize_result(result)

    def get_improvement_summary(self, score_result: dict) -> str:
        score_result = self._normalize_result(score_result)
        lines = [
            f"STRICT ATS SCORE: {score_result['score']}/100",
            f"ATS CONFIDENCE: {score_result['ats_confidence']}",
            f"RECRUITER CONFIDENCE: {score_result['recruiter_confidence']}",
        ]
        if score_result.get("top_fixes"):
            lines.append("TOP FIXES:")
            for i, item in enumerate(score_result["top_fixes"][:8], 1):
                lines.append(f"  {i}. {item}")
        wf = score_result.get("writer_feedback", {})
        if wf:
            lines.append("WRITER FEEDBACK:")
            if wf.get("core_ownership_areas"):
                lines.append("  Ownership areas: " + ", ".join(wf["core_ownership_areas"]))
            if wf.get("skills_to_emphasize"):
                lines.append("  Emphasize in bullets: " + ", ".join(wf["skills_to_emphasize"]))
            if wf.get("skills_ok_in_skills_only"):
                lines.append("  Skills-only is okay for: " + ", ".join(wf["skills_ok_in_skills_only"]))
        return "\n".join(lines)

    def _call_model(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            output_text = getattr(response, "output_text", None)
            if isinstance(output_text, str) and output_text.strip():
                return output_text
            collected: List[str] = []
            output_items = getattr(response, "output", None)
            if isinstance(output_items, list):
                for item in output_items:
                    item_content = getattr(item, "content", None)
                    if isinstance(item_content, list):
                        for c in item_content:
                            text_val = getattr(c, "text", None)
                            if isinstance(text_val, str) and text_val.strip():
                                collected.append(text_val)
            return "\n".join(collected).strip()
        except Exception:
            chat_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
            )
            content = ""
            if getattr(chat_response, "choices", None):
                choice = chat_response.choices[0] if chat_response.choices else None
                if choice and getattr(choice, "message", None):
                    content = choice.message.content or ""
            return str(content or "")

    def _parse_result(self, content: str) -> dict:
        content = str(content or "").strip()
        if "```json" in content:
            content = content.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0].strip()
        if not content:
            result = self._default_result()
            result["forced_or_generic_signals"] = ["Model returned empty content."]
            result["wording_gaps"] = ["Empty model response"]
            result["top_fixes"] = ["Retry scorer request"]
            return result
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        result = self._default_result()
        result["forced_or_generic_signals"] = ["Failed to parse model output."]
        result["wording_gaps"] = [f"Scorer output was not valid JSON. Raw output starts with: {content[:240]}"]
        result["top_fixes"] = ["Tighten scorer prompt to force strict JSON output."]
        return result

    def _normalize_resume_content(self, resume_content: dict) -> dict:
        if not isinstance(resume_content, dict):
            return {"summary": [], "skills": {}, "bee_data": [], "allied_health": [], "byjus": [], "cognizant": []}
        normalized = dict(resume_content)
        summary = normalized.get("summary")
        if summary is None:
            normalized["summary"] = []
        elif not isinstance(summary, list):
            normalized["summary"] = [str(summary)]
        skills = normalized.get("skills")
        if skills is None:
            normalized["skills"] = {}
        elif not isinstance(skills, dict):
            normalized["skills"] = {"General": str(skills)}
        for section in ["bee_data", "allied_health", "byjus", "cognizant"]:
            value = normalized.get(section)
            if value is None:
                normalized[section] = []
            elif isinstance(value, list):
                normalized[section] = [str(x) for x in value if x is not None]
            else:
                normalized[section] = [str(value)]
        return normalized

    def _extract_resume_structure(self, resume_content: dict) -> dict:
        return {
            "summary": resume_content.get("summary", []),
            "skills": resume_content.get("skills", {}),
            "experience": {
                "bee_data": resume_content.get("bee_data", []),
                "allied_health": resume_content.get("allied_health", []),
                "byjus": resume_content.get("byjus", []),
                "cognizant": resume_content.get("cognizant", []),
            },
        }

    def _format_resume_for_review(self, resume_content: dict) -> str:
        lines: List[str] = []
        if resume_content.get("summary"):
            lines.append("## SUMMARY")
            for item in resume_content["summary"]:
                lines.append(f"- {item}")
        if resume_content.get("skills"):
            lines.append("\n## TECHNICAL SKILLS")
            for category, value in resume_content["skills"].items():
                lines.append(f"{category}: {value}")
        mapping = {"bee_data": "## BEE DATA TECHNOLOGIES", "allied_health": "## ALLIED HEALTH AGENCY", "byjus": "## BYJU'S", "cognizant": "## COGNIZANT"}
        for key, header in mapping.items():
            if resume_content.get(key):
                lines.append(f"\n{header}")
                for bullet in resume_content[key]:
                    lines.append(f"- {bullet}")
        return "\n".join(lines)

    def _extract_jd_signals(self, job_description: str) -> dict:
        jd_lower = (job_description or "").lower()
        candidates = [
            "python", "java", "sql", "aws", "azure", "sagemaker", "docker", "kubernetes",
            "langchain", "langgraph", "crewai", "pydantic", "llm", "rag", "vector databases",
            "embeddings", "monitoring", "retraining", "documentation", "agile",
            "governance", "architecture", "reference architecture", "blueprint",
            "pi planning", "art", "architectural runway", "vendor evaluation",
            "model registry", "experiment tracking", "feature engineering",
            "computer vision", "recommender systems", "responsible ai", "bias mitigation",
            "explainability", "api", "orchestration", "mentoring", "security", "compliance"
        ]
        explicit = [x for x in candidates if x in jd_lower]
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
                if term in self.core_capability_terms:
                    is_replaceable_fulltime = job_type.lower() == "fulltime" and term in self.replaceable_terms
                    if not is_replaceable_fulltime and not (in_summary or in_skills):
                        unsupported_core.append(term)
        generic_hits = [phrase for phrase in self.generic_phrases if phrase in (summary_text + " " + bullets_text)]
        repetitive_starts = self._repetitive_starts(bullets)
        vague_bullets = [b for b in bullets if self._is_vague_bullet(b)]
        overloaded_bullets = [b for b in bullets if self._is_overloaded_bullet(b)]
        grounded_bullets = [b for b in bullets if self._is_grounded_bullet(b)]
        metrics_ratio = self._metrics_ratio(bullets)
        role_scope = self._role_scope(structured_resume["experience"])
        return {
            "evidence": evidence,
            "unsupported_core": unsupported_core[:10],
            "generic_hits": generic_hits[:10],
            "repetitive_starts": repetitive_starts,
            "vague_bullets": vague_bullets[:8],
            "overloaded_bullets": overloaded_bullets[:8],
            "grounded_bullets": grounded_bullets[:8],
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
        weak_patterns = ["worked on", "worked with", "responsible for", "helped with", "strong experience", "demonstrated ability", "proven track record"]
        has_weak = any(p in lower for p in weak_patterns)
        has_object = any(x in lower for x in self.data_object_terms)
        has_metric = bool(re.search(r"\d+%|\d[\d,]*\+?|\bms\b|\busers\b|\brequests\b", lower))
        return has_weak and not has_object and not has_metric

    def _is_overloaded_bullet(self, bullet: str) -> bool:
        lower = bullet.lower()
        tool_count = len(re.findall(r"\b(aws|azure|sagemaker|docker|kubernetes|langchain|langgraph|openai|pytorch|tensorflow|spark|sql|java|crewai|pydantic|api)\b", lower))
        has_metric = bool(re.search(r"\d+%|\d[\d,]*\+?", lower))
        has_object = any(x in lower for x in self.data_object_terms)
        return tool_count >= 4 and not has_metric and not has_object

    def _is_grounded_bullet(self, bullet: str) -> bool:
        lower = bullet.lower()
        has_object = any(x in lower for x in self.data_object_terms)
        has_system = bool(re.search(r"\b(aws|azure|sagemaker|docker|kubernetes|endpoint|batch inference|api|langchain|langgraph|vector|registry)\b", lower))
        has_result = bool(re.search(r"\d+%|\d[\d,]*\+?|\bimprov|\breduc|\bincreas|\bmaintain|\bsupport|\bserve|\benable|\bdeliver", lower))
        return has_object and has_system and has_result

    def _metrics_ratio(self, bullets: List[str]) -> float:
        if not bullets:
            return 0.0
        metric_count = sum(1 for b in bullets if re.search(r"\d+%|\d[\d,]*\+?|\bms\b|\busers\b|\brequests\b", b.lower()))
        return round(metric_count / len(bullets), 2)

    def _role_scope(self, experience: Dict[str, List[str]]) -> Dict[str, Any]:
        domain_map = {
            "ml_platform": ["sagemaker", "registry", "endpoint", "monitoring", "retraining"],
            "llm_apps": ["openai", "rag", "langchain", "langgraph", "vector", "prompt"],
            "backend": ["api", "fastapi", "oauth", "service", "java"],
            "data": ["spark", "etl", "warehouse", "feature engineering", "data pipeline"],
            "architecture": ["architecture", "blueprint", "guardrail", "review", "roadmap", "vendor", "governance"],
        }
        result: Dict[str, Any] = {}
        for role, bullets in experience.items():
            text = " ".join(bullets).lower()
            active = []
            for domain, keywords in domain_map.items():
                if sum(1 for kw in keywords if kw in text) >= 2:
                    active.append(domain)
            result[role] = {"active_domains": active, "too_broad": len(active) >= 4}
        return result

    def _default_result(self) -> dict:
        return {
            "score": 0,
            "passed": False,
            "ats_confidence": "low",
            "recruiter_confidence": "low",
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

    def _normalize_result(self, result: Any) -> dict:
        defaults = self._default_result()
        if not isinstance(result, dict):
            return defaults
        for key, default_value in defaults.items():
            if key not in result or result[key] is None:
                result[key] = default_value
        if not isinstance(result["breakdown"], dict):
            result["breakdown"] = defaults["breakdown"]
        else:
            for k, v in defaults["breakdown"].items():
                if k not in result["breakdown"] or result["breakdown"][k] is None:
                    result["breakdown"][k] = v
        for key in ["evidence_strength", "writer_feedback"]:
            if not isinstance(result[key], dict):
                result[key] = defaults[key]
            else:
                for k, v in defaults[key].items():
                    if k not in result[key] or result[key][k] is None:
                        result[key][k] = v
        for key in ["forced_or_generic_signals", "skill_gaps", "wording_gaps", "top_fixes", "strengths"]:
            if not isinstance(result[key], list):
                result[key] = defaults[key]
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
        elif heuristic["grounded_bullets"]:
            recruiter_conf = "medium" if recruiter_conf == "low" else recruiter_conf
        forced = list(result.get("forced_or_generic_signals", []))
        forced += [f"Generic phrase used: {x}" for x in heuristic["generic_hits"][:6]]
        forced += [f"Vague bullet: {x}" for x in heuristic["vague_bullets"][:3]]
        forced += [f"Overloaded bullet: {x}" for x in heuristic["overloaded_bullets"][:3]]
        result["forced_or_generic_signals"] = forced[:12]
        wording_gaps = list(result.get("wording_gaps", []))
        if heuristic["repetitive_starts"]:
            wording_gaps.append("Repeated bullet openings reduce natural tone: " + ", ".join(f"{k} ({v}x)" for k, v in heuristic["repetitive_starts"].items()))
        if heuristic["vague_bullets"]:
            wording_gaps.append("Some bullets need a clearer object, operational step, or result.")
        if heuristic["overloaded_bullets"]:
            wording_gaps.append("Some bullets contain too many tools without enough grounding.")
        result["wording_gaps"] = wording_gaps[:10]
        skill_gaps = list(result.get("skill_gaps", []))
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
        skills_to_emphasize = [x for x in jd_signals["explicit"] if x not in self.granular_skill_terms and not (job_type.lower() == "fulltime" and x in self.replaceable_terms)][:12]
        skills_ok_in_skills_only = [x for x in jd_signals["explicit"] if x in self.granular_skill_terms or (job_type.lower() == "fulltime" and x in self.replaceable_terms)][:12]
        bad_patterns = [
            "Do not write summary bullets like pasted JD lines.",
            "Do not use proven track record, demonstrated ability, deep expertise, or strong experience.",
            "Do not stack 4 or more tools in a bullet unless the workflow truly requires it.",
            "Do not claim enterprise architecture or governance ownership beyond what the work history supports.",
            "Do not force defense, clearance, or national-security positioning unless extensively proven.",
            "Do not repeat the same phrase root across multiple bullets in one section."
        ]
        rewrite_examples = [
            {"bad": "Worked on SageMaker, Docker, Kubernetes, and MLflow for model deployment.", "better": "Built SageMaker deployment workflows for batch and real-time inference, packaged services in Docker, and tracked model versions in MLflow to support controlled releases."},
            {"bad": "Strong experience with machine learning and large language models.", "better": "Built production ML workflows and LLM-based retrieval services used in customer support and document search flows."},
            {"bad": "Responsible for model monitoring and retraining.", "better": "Implemented monitoring for prediction drift and response quality, then triggered retraining jobs when service thresholds were breached."},
            {"bad": "Used LangChain and OpenAI for RAG.", "better": "Developed a RAG workflow that retrieved policy content from a vector index and injected grounded context into GPT responses for support teams."},
            {"bad": "Designed enterprise AI architecture strategy and standards.", "better": "Provided solution-level AI design guidance for integration patterns, model lifecycle decisions, and review checkpoints across delivery teams."},
            {"bad": "Worked with healthcare data and ML models.", "better": "Processed healthcare call transcripts and policy documents to build classification and retrieval workflows supporting agent assistance and document search."},
        ]
        summary_guidance = "Write summary with about 60% target-role alignment and 40% systems, production actions, or business context. Keep summary metric-free. Avoid forced domain branding, defense wording, or inflated architect claims."
        top_fixes = list(result.get("top_fixes", []))
        if heuristic["vague_bullets"]:
            top_fixes.append("Replace vague bullets with object + action + system + result wording.")
        if heuristic["overloaded_bullets"]:
            top_fixes.append("Split overloaded bullets so each one focuses on one workflow and one outcome.")
        if heuristic["unsupported_core"]:
            top_fixes.append("Emphasize core JD capabilities in work bullets, while leaving replaceable or granular items in Skills if needed.")
        if any(v.get("too_broad") for v in heuristic["role_scope"].values()) and job_type.lower() == "fulltime":
            top_fixes.append("Reduce breadth in at least one role so the profile feels focused rather than inflated.")
        result["top_fixes"] = top_fixes[:10]
        strengths = list(result.get("strengths", []))
        if heuristic["grounded_bullets"]:
            strengths.append("Some bullets already sound grounded and operational rather than keyword-driven.")
        result["strengths"] = strengths[:8]
        return {
            "core_ownership_areas": core_areas,
            "skills_to_emphasize": skills_to_emphasize,
            "skills_ok_in_skills_only": skills_ok_in_skills_only,
            "bad_patterns_to_avoid": bad_patterns,
            "rewrite_examples": rewrite_examples,
            "summary_guidance": summary_guidance,
        }

    def _infer_ownership_areas(self, explicit_terms: List[str]) -> List[str]:
        terms = set(explicit_terms)
        areas = []
        if {"sagemaker", "model registry", "batch inference", "monitoring", "retraining"} & terms:
            areas.append("model lifecycle and inference workflows")
        if {"feature engineering", "aws", "azure", "sql"} & terms:
            areas.append("data ingestion and feature engineering pipelines")
        if {"openai", "llm", "rag", "langchain", "langgraph", "crewai", "vector databases", "embeddings"} & terms:
            areas.append("llm application and orchestration workflows")
        if {"docker", "kubernetes", "api"} & terms:
            areas.append("containerized deployment and runtime operations")
        if {"governance", "architecture", "reference architecture", "blueprint", "vendor evaluation"} & terms:
            areas.append("solution architecture, standards, and review guidance")
        if {"documentation", "agile", "pi planning", "architectural runway", "mentoring"} & terms:
            areas.append("delivery planning, documentation, and cross-team guidance")
        return areas[:7]


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    scorer = ScorerAgent()
    test_jd = """
Senior AI Engineer
Requirements:
- Python
- Java
- LangChain or CrewAI
- LLMs
- monitoring
"""
    test_resume = {
        "summary": ["AI engineer with 5+ years building LLM workflows."],
        "skills": {"Programming": "Python, Java", "AI Frameworks": "LangChain, CrewAI"},
        "bee_data": ["Built LangChain-based RAG workflow and monitored model quality in production."],
        "allied_health": ["Developed Python APIs for ML inference."],
        "byjus": ["Trained classification models using scikit-learn."],
        "cognizant": ["Developed backend services and automation scripts."]
    }
    result = scorer.score_resume(test_jd, test_resume, job_type="Fulltime")
    print(json.dumps(result, indent=2))
