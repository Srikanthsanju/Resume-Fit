"""
Mode-aware ATS scorer

- Uses OpenAI GPT-5 via Responses API
- Scores differently for Fulltime and Contract
- Separates ATS fit from recruiter trust
- Gives writer-ready feedback with examples
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
        path = config_dir / "guidelines.md"
        if path.exists():
            self.guidelines = path.read_text(encoding="utf-8")

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
            "redis", "postgresql", "snowflake", "bigquery", "encryption",
            "service bus", "cosmos db", "application insights"
        }

        self.data_object_terms = [
            "call transcript", "policy document", "resume", "job listing", "training dataset",
            "feature table", "vector index", "model artifact", "endpoint", "batch job",
            "api request", "document corpus", "customer profile", "warehouse table",
            "invoice", "ticket", "knowledge base", "document archive"
        ]

    def score_resume(self, job_description: str, resume_content: dict, job_type: str = "Fulltime") -> dict:
        resume_content = self._normalize_resume_content(resume_content)
        structured = self._extract_resume_structure(resume_content)
        resume_text = self._format_resume_for_review(resume_content)
        jd = self._extract_jd_signals(job_description)
        heuristic = self._heuristic_analysis(structured, jd, job_type)

        system_prompt = f"""
You are a strict ATS and recruiter-trust evaluator.

Job type: {job_type}

Rules:
- Score ATS fit and recruiter trust separately.
- Do not over-penalize rulebook-approved differences such as summary length, date mode, or selective emphasis of replaceable skills.
- Fulltime mode should be stricter on realism and inflated claims.
- Contract mode should be more tolerant of longer bullets, repeated skills, deeper detail, and vendor-style JD mirroring when still believable.
- Granular tools may appear only in Skills without a heavy penalty.
- Replaceable skills do not need equal emphasis in Fulltime mode.

Return only valid JSON with this shape:
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
Give feedback that a writer can use directly in the next iteration.
Return only JSON.
"""

        raw = self._call_model(system_prompt, user_prompt)
        result = self._parse_result(raw)
        result = self._normalize_result(result)
        result = self._apply_post_adjustments(result, heuristic, jd, job_type)
        result["writer_feedback"] = self._build_writer_feedback(result, heuristic, jd, job_type)
        return self._normalize_result(result)

    def get_improvement_summary(self, score_result: dict) -> str:
        score_result = self._normalize_result(score_result)
        parts = [
            f"STRICT ATS SCORE: {score_result['score']}/100",
            f"ATS CONFIDENCE: {score_result['ats_confidence']}",
            f"RECRUITER CONFIDENCE: {score_result['recruiter_confidence']}",
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
                parts.append("  Emphasize in bullets: " + ", ".join(wf["skills_to_emphasize"]))
            if wf.get("skills_ok_in_skills_only"):
                parts.append("  Skills-only is okay for: " + ", ".join(wf["skills_ok_in_skills_only"]))
        return "\n".join(parts)

    def _call_model(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            if isinstance(getattr(response, "output_text", None), str) and response.output_text.strip():
                return response.output_text

            collected: List[str] = []
            output_items = getattr(response, "output", None)
            if isinstance(output_items, list):
                for item in output_items:
                    content = getattr(item, "content", None)
                    if isinstance(content, list):
                        for c in content:
                            txt = getattr(c, "text", None)
                            if isinstance(txt, str) and txt.strip():
                                collected.append(txt)
            return "\n".join(collected).strip()

        except Exception:
            chat = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
            )
            if getattr(chat, "choices", None):
                choice = chat.choices[0] if chat.choices else None
                if choice and getattr(choice, "message", None):
                    return str(choice.message.content or "")
            return ""

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
        for key, value in defaults.items():
            if key not in result or result[key] is None:
                result[key] = value
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

    def _parse_result(self, raw: str) -> dict:
        raw = str(raw or "").strip()
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
        if not raw:
            result = self._default_result()
            result["wording_gaps"] = ["Empty model response"]
            result["top_fixes"] = ["Retry scorer request"]
            return result
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        result = self._default_result()
        result["wording_gaps"] = [f"Scorer output was not valid JSON. Raw output starts with: {raw[:240]}"]
        result["top_fixes"] = ["Force stricter JSON output in scorer prompt"]
        return result

    def _normalize_resume_content(self, resume_content: Any) -> dict:
        if not isinstance(resume_content, dict):
            return {
                "summary": [],
                "skills": {},
                "experience_1": [],
                "experience_2": [],
                "experience_3": [],
                "experience_4": [],
            }
        out = dict(resume_content)
        if not isinstance(out.get("summary"), list):
            out["summary"] = [] if out.get("summary") is None else [str(out["summary"])]
        if not isinstance(out.get("skills"), dict):
            out["skills"] = {} if out.get("skills") is None else {"General": str(out["skills"])}
        for key in ["experience_1", "experience_2", "experience_3", "experience_4", "bee_data", "allied_health", "byjus", "cognizant"]:
            if key in out:
                if out[key] is None:
                    out[key] = []
                elif isinstance(out[key], list):
                    out[key] = [str(x) for x in out[key] if x is not None]
                else:
                    out[key] = [str(out[key])]

        for old, new in [("bee_data", "experience_1"), ("allied_health", "experience_2"), ("byjus", "experience_3"), ("cognizant", "experience_4")]:
            if not out.get(new):
                out[new] = out.get(old, [])

        return out

    def _extract_resume_structure(self, resume_content: dict) -> dict:
        return {
            "summary": resume_content.get("summary", []),
            "skills": resume_content.get("skills", {}),
            "experience": {
                "experience_1": resume_content.get("experience_1", []),
                "experience_2": resume_content.get("experience_2", []),
                "experience_3": resume_content.get("experience_3", []),
                "experience_4": resume_content.get("experience_4", []),
            }
        }

    def _format_resume_for_review(self, resume_content: dict) -> str:
        lines: List[str] = []
        if resume_content.get("summary"):
            lines.append("## SUMMARY")
            for b in resume_content["summary"]:
                lines.append(f"- {b}")
        if resume_content.get("skills"):
            lines.append("\n## TECHNICAL SKILLS")
            for k, v in resume_content["skills"].items():
                lines.append(f"{k}: {v}")
        for key in ["experience_1", "experience_2", "experience_3", "experience_4"]:
            if resume_content.get(key):
                lines.append(f"\n## {key.upper()}")
                for b in resume_content[key]:
                    lines.append(f"- {b}")
        return "\n".join(lines)

    def _extract_jd_signals(self, job_description: str) -> dict:
        jd_lower = (job_description or "").lower()
        candidates = [
            "python", "java", "typescript", "sql", "aws", "azure", "gcp",
            "sagemaker", "docker", "kubernetes", "langchain", "langgraph", "crewai",
            "pydantic", "semantic kernel", "llm", "rag", "vector databases", "embeddings",
            "monitoring", "retraining", "documentation", "agile", "governance",
            "architecture", "reference architecture", "blueprint", "pi planning", "art",
            "architectural runway", "vendor evaluation", "model registry",
            "experiment tracking", "feature engineering", "computer vision",
            "recommender systems", "responsible ai", "bias mitigation", "explainability",
            "api", "orchestration", "mentoring", "security", "compliance",
            "bedrock", "agentcore", "mcp", "a2a", "cloudwatch", "fastapi",
            "lambda", "eks", "observability", "prompt engineering", "fine-tuning", "evaluation"
        ]
        return {"raw": job_description, "explicit": [c for c in candidates if c in jd_lower]}

    def _heuristic_analysis(self, structured: dict, jd: dict, job_type: str) -> dict:
        summary_text = " ".join(structured["summary"]).lower()
        skills_text = " ".join(f"{k} {v}" for k, v in structured["skills"].items()).lower()
        bullets = [b for sec in structured["experience"].values() for b in sec]
        bullets_text = " ".join(bullets).lower()

        evidence = {"strong": [], "medium": [], "weak_or_missing": []}
        unsupported_core = []

        for term in jd["explicit"]:
            exp_hits = sum(1 for b in bullets if term in b.lower())
            in_summary = term in summary_text
            in_skills = term in skills_text

            if exp_hits >= 2:
                evidence["strong"].append(term)
            elif exp_hits == 1:
                evidence["medium"].append(term)
            else:
                evidence["weak_or_missing"].append(term)
                if term not in self.granular_skill_terms:
                    is_replaceable_fulltime = job_type.lower() == "fulltime" and term in self.replaceable_terms
                    if not is_replaceable_fulltime and not (in_summary or in_skills):
                        unsupported_core.append(term)

        generic_hits = [p for p in self.generic_phrases if p in (summary_text + " " + bullets_text)]
        repetitive = self._repetitive_starts(bullets)
        vague = [b for b in bullets if self._is_vague_bullet(b)]
        overloaded = [b for b in bullets if self._is_overloaded_bullet(b, job_type)]
        grounded = [b for b in bullets if self._is_grounded_bullet(b)]
        metrics_ratio = self._metrics_ratio(bullets)
        bullet_count = len(bullets)

        return {
            "evidence": evidence,
            "unsupported_core": unsupported_core[:12],
            "generic_hits": generic_hits[:10],
            "repetitive_starts": repetitive,
            "vague_bullets": vague[:8],
            "overloaded_bullets": overloaded[:8],
            "grounded_bullets": grounded[:8],
            "metrics_ratio": metrics_ratio,
            "bullet_count": bullet_count,
            "job_type": job_type,
        }

    def _repetitive_starts(self, bullets: List[str]) -> Dict[str, int]:
        c = Counter()
        for b in bullets:
            words = b.strip().split()
            if words:
                c[words[0].lower()] += 1
        return {k: v for k, v in c.items() if v >= 3}

    def _is_vague_bullet(self, bullet: str) -> bool:
        lower = bullet.lower()
        weak = ["worked on", "worked with", "responsible for", "helped with", "demonstrated ability"]
        has_weak = any(x in lower for x in weak)
        has_object = any(x in lower for x in self.data_object_terms)
        has_metric = bool(re.search(r"\d+%|\d[\d,]*\+?|\bms\b|\busers\b|\brequests\b", lower))
        return has_weak and not has_object and not has_metric

    def _is_overloaded_bullet(self, bullet: str, job_type: str) -> bool:
        lower = bullet.lower()
        tool_count = len(re.findall(r"\b(aws|azure|gcp|sagemaker|docker|kubernetes|langchain|langgraph|openai|pytorch|tensorflow|spark|sql|java|crewai|pydantic|api|bedrock|agentcore|lambda|eks)\b", lower))
        has_metric = bool(re.search(r"\d+%|\d[\d,]*\+?", lower))
        has_object = any(x in lower for x in self.data_object_terms)
        threshold = 5 if job_type.lower() == "contract" else 4
        return tool_count >= threshold and not has_metric and not has_object

    def _is_grounded_bullet(self, bullet: str) -> bool:
        lower = bullet.lower()
        has_object = any(x in lower for x in self.data_object_terms)
        has_system = bool(re.search(r"\b(aws|azure|gcp|sagemaker|docker|kubernetes|endpoint|batch inference|api|langchain|langgraph|vector|registry|bedrock|agentcore)\b", lower))
        has_result = bool(re.search(r"\d+%|\d[\d,]*\+?|\bimprov|\breduc|\bincreas|\bmaintain|\bsupport|\bserve|\benable|\bdeliver", lower))
        return has_object and has_system and has_result

    def _metrics_ratio(self, bullets: List[str]) -> float:
        if not bullets:
            return 0.0
        count = sum(1 for b in bullets if re.search(r"\d+%|\d[\d,]*\+?|\bms\b|\busers\b|\brequests\b", b.lower()))
        return round(count / len(bullets), 2)

    def _apply_post_adjustments(self, result: dict, heuristic: dict, jd: dict, job_type: str) -> dict:
        score = int(result.get("score", 0))

        score -= min(len(heuristic["generic_hits"]) * (3 if job_type.lower() == "fulltime" else 1), 10)
        score -= min(len(heuristic["vague_bullets"]) * (2 if job_type.lower() == "fulltime" else 1), 8)
        score -= min(len(heuristic["overloaded_bullets"]) * (2 if job_type.lower() == "fulltime" else 1), 8)

        if heuristic["metrics_ratio"] < 0.2:
            score -= 3 if job_type.lower() == "fulltime" else 1

        if len(heuristic["unsupported_core"]) >= 5:
            score = min(score, 84 if job_type.lower() == "fulltime" else 90)

        if job_type.lower() == "contract":
            if heuristic["bullet_count"] >= 36:
                score += 3
            elif heuristic["bullet_count"] >= 28:
                score += 1

        result["score"] = max(0, min(score, 100))
        result["passed"] = result["score"] >= 85

        recruiter_conf = result.get("recruiter_confidence", "medium")
        if heuristic["vague_bullets"] and job_type.lower() == "fulltime":
            recruiter_conf = "low" if recruiter_conf != "high" else "medium"
        elif heuristic["grounded_bullets"]:
            recruiter_conf = "medium" if recruiter_conf == "low" else recruiter_conf
        result["recruiter_confidence"] = recruiter_conf

        result["evidence_strength"] = heuristic["evidence"]

        forced = list(result.get("forced_or_generic_signals", []))
        forced += [f"Generic phrase used: {x}" for x in heuristic["generic_hits"][:6]]
        if job_type.lower() == "fulltime":
            forced += [f"Overloaded bullet: {x}" for x in heuristic["overloaded_bullets"][:3]]
        result["forced_or_generic_signals"] = forced[:12]

        wording = list(result.get("wording_gaps", []))
        if heuristic["repetitive_starts"] and job_type.lower() == "fulltime":
            wording.append("Repeated bullet openings reduce natural tone: " + ", ".join(f"{k} ({v}x)" for k, v in heuristic["repetitive_starts"].items()))
        if heuristic["vague_bullets"]:
            wording.append("Some bullets need a clearer object, operational step, or result.")
        if heuristic["overloaded_bullets"] and job_type.lower() == "fulltime":
            wording.append("Some bullets contain too many tools without enough grounding.")
        result["wording_gaps"] = wording[:10]

        skill_gaps = list(result.get("skill_gaps", []))
        for s in heuristic["unsupported_core"][:8]:
            skill_gaps.append(f"Core skill not clearly supported by work history: {s}")
        result["skill_gaps"] = skill_gaps[:12]

        return result

    def _build_writer_feedback(self, result: dict, heuristic: dict, jd: dict, job_type: str) -> dict:
        core_areas = self._infer_ownership_areas(jd["explicit"])
        emphasize = [x for x in jd["explicit"] if x not in self.granular_skill_terms and not (job_type.lower() == "fulltime" and x in self.replaceable_terms)][:12]
        skills_only = [x for x in jd["explicit"] if x in self.granular_skill_terms or (job_type.lower() == "fulltime" and x in self.replaceable_terms)][:12]

        bad_patterns = [
            "Do not write summary bullets like pasted JD lines.",
            "Do not use proven track record, demonstrated ability, deep expertise, or strong experience.",
            "Do not stack too many tools into one bullet without explaining the workflow.",
            "Do not claim enterprise authority or governance ownership beyond what the work history supports.",
            "Do not force defense, clearance, or national-security positioning unless extensively proven.",
        ]

        rewrite_examples = [
            {
                "bad": "Worked on Bedrock, Lambda, CloudWatch, and EKS for agent deployment.",
                "better": "Built Bedrock-backed agent workflows, deployed runtime services on Lambda and EKS based on workload needs, and tracked latency and failures through CloudWatch dashboards."
            },
            {
                "bad": "Strong experience with LLMs and prompt engineering.",
                "better": "Designed prompt templates, evaluation checks, and fine-tuning workflows to improve response quality and reduce hallucination rates in production GenAI services."
            },
            {
                "bad": "Responsible for multi-agent orchestration.",
                "better": "Defined LangGraph orchestration patterns for task-specific agents, tool routing, and response synthesis across production workflows."
            },
            {
                "bad": "Used vector database and embeddings for RAG.",
                "better": "Designed chunking strategy, embedding flow, and vector retrieval configuration for a RAG pipeline serving grounded document responses."
            },
        ]

        summary_guidance = (
            "Write summary with about 60% role and JD alignment and 40% systems, production actions, or business context. "
            "Keep summary metric-free. In Contract mode, allow more bullets and keyword density. In Fulltime mode, keep summary tighter and more selective."
        )

        return {
            "core_ownership_areas": core_areas,
            "skills_to_emphasize": emphasize,
            "skills_ok_in_skills_only": skills_only,
            "bad_patterns_to_avoid": bad_patterns,
            "rewrite_examples": rewrite_examples,
            "summary_guidance": summary_guidance,
        }

    def _infer_ownership_areas(self, explicit_terms: List[str]) -> List[str]:
        terms = set(explicit_terms)
        areas = []
        if {"sagemaker", "model registry", "monitoring", "retraining", "fine-tuning", "evaluation"} & terms:
            areas.append("model lifecycle and evaluation workflows")
        if {"rag", "vector databases", "embeddings", "feature engineering"} & terms:
            areas.append("retrieval and data preparation workflows")
        if {"openai", "llm", "langchain", "langgraph", "crewai", "semantic kernel", "orchestration", "mcp", "a2a"} & terms:
            areas.append("agentic orchestration and llm application workflows")
        if {"docker", "kubernetes", "lambda", "eks", "api", "fastapi", "cloudwatch", "observability"} & terms:
            areas.append("runtime deployment, observability, and API operations")
        if {"governance", "architecture", "reference architecture", "vendor evaluation", "blueprint", "responsible ai", "explainability"} & terms:
            areas.append("architecture, standards, and governance guidance")
        if {"documentation", "agile", "pi planning", "architectural runway", "mentoring"} & terms:
            areas.append("delivery planning, documentation, and technical mentorship")
        return areas[:7]

