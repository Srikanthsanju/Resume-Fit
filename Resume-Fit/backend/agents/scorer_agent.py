"""
Strict ATS + Resume Realism Scorer

What this version fixes:
1. Does NOT hand out 90%+ just because keywords exist in summary/skills.
2. Requires evidence of skills inside work experience bullets.
3. Penalizes generic, forced, or buzzword-heavy wording.
4. Checks domain coherence and whether tools sound realistically used.
5. Produces stricter ATS scoring and recruiter-style feedback.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Any

from openai import OpenAI


class ScorerAgent:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

        config_dir = Path(__file__).parent.parent / "config"
        self.guidelines = ""
        guidelines_path = config_dir / "guidelines.md"
        if guidelines_path.exists():
            self.guidelines = guidelines_path.read_text(encoding="utf-8")

        # Generic / inflated wording patterns that often make resumes sound fake.
        # Keep this list conservative so we do not punish normal resume language too aggressively.
        self.generic_phrases = [
            "proven track record",
            "demonstrated ability",
            "deep background",
            "cutting-edge",
            "world-class",
            "best-in-class",
            "delivering business value",
            "robust solutions",
        ]

        # Granular tools are acceptable in Skills even if not repeated in bullets.
        # We only penalize missing evidence for core capabilities that should be visible in work history.
        self.core_capability_terms = {
            "python", "sql", "aws", "sagemaker", "sagemaker pipelines", "model registry",
            "experiment tracking", "hyperparameter tuning", "batch inference", "managed endpoints",
            "docker", "kubernetes", "mlops", "ci/cd", "monitoring", "retraining",
            "feature engineering", "pytorch", "tensorflow", "scikit-learn", "xgboost",
            "openai", "llm", "rag"
        }

        # Granular or supporting tools may live only in Skills.
        self.granular_skill_terms = {
            "glue", "ecr", "iam", "vpc", "athena", "redshift", "lambda", "emr",
            "cloudwatch", "bedrock", "fastapi", "langgraph", "llamaindex", "redis",
            "postgresql", "snowflake", "bigquery", "encryption", "access controls"
        }

        # Resume wording patterns that often sound generated or inflated
        self.weak_claim_patterns = [
            r"\bresponsible for\b",
            r"\bworked on\b",
            r"\bworked with\b",
            r"\bhelped with\b",
            r"\binvolved in\b",
            r"\bvarious\b",
            r"\bmultiple\b",
            r"\bseveral\b",
            r"\busing [A-Za-z0-9 ,/\-]+ for [A-Za-z0-9 ,/\-]+ for\b",
            r"\bdesign and implement\b",
            r"\bbuild and deploy\b",
            r"\bdevelop and maintain\b",
        ]

        # Realistic engineering signals. These usually make bullets sound lived-in.
        self.real_workflow_signals = {
            "data_movement": ["ingest", "extracted", "loaded", "parsed", "transformed", "joined", "partitioned"],
            "serving": ["endpoint", "batch inference", "real-time", "latency", "throughput", "autoscaling"],
            "training": ["training job", "hyperparameter", "cross-validation", "evaluation", "registry", "drift"],
            "ops": ["alert", "rollback", "failure", "retry", "scheduler", "trigger", "deployed"],
            "security": ["iam", "vpc", "kms", "encryption", "access policy", "private subnet"],
        }

        # Domain-specific nouns that make bullets more believable when tied to actions
        self.concrete_object_terms = [
            "resume", "job listing", "policy document", "call transcript", "feature table",
            "training dataset", "inference endpoint", "model artifact", "prediction payload",
            "embedding", "vector index", "warehouse table", "batch job", "api request"
        ]

        # Action verbs we want to see, but not too repetitively
        self.good_verbs = {
            "built", "designed", "developed", "implemented", "deployed", "engineered",
            "trained", "optimized", "operationalized", "orchestrated", "configured",
            "automated", "integrated", "monitored", "reduced", "improved", "created",
            "migrated", "scaled", "validated", "tracked", "served"
        }

    # ---------- Public API ----------

    def score_resume(self, job_description: str, resume_content: dict) -> dict:
        resume_text = self._format_resume_for_review(resume_content)
        structured_resume = self._extract_resume_structure(resume_content, resume_text)
        jd_signals = self._extract_jd_signals(job_description)
        evidence = self._build_evidence_map(structured_resume, jd_signals)

        heuristic = self._heuristic_analysis(job_description, structured_resume, jd_signals, evidence)

        system_prompt = """
You are a STRICT ATS and recruiter-quality resume evaluator.

You do NOT reward resumes merely for listing keywords in summary or skills.
You care about:
1. evidence inside work experience
2. realistic wording
3. believable tool usage
4. domain consistency
5. whether bullets show actual work, not keyword stuffing

Important scoring rules:
- Core capabilities get full credit only when supported by believable work bullets.
- Summary and skills sections alone are weaker evidence than work experience.
- Granular tools can appear only in the Skills section without a heavy penalty.
- Do NOT punish the resume for omitting every granular tool from bullets if the core workflow is clearly evidenced.
- Generic wording, buzzword stacking, and vague claims must reduce score.
- Resume should sound like a real engineer wrote it, not an AI keyword generator.
- Penalize forced tool insertion if the bullet does not explain what the tool did.
- Penalize overly broad "did everything" profiles unless backed by concrete scope.
- Prefer bullets that show a real workflow: source/data/object, action, system/tool, and operational outcome.
- Penalize bullets that sound templated, stacked, or vague even if they include the right tools.
- Distinguish ATS score from recruiter confidence. A resume can match keywords and still have weak credibility.

Return ONLY valid JSON in this schema:
{
  "score": 0,
  "passed": false,
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
  "evidence_strength": {
    "strong": [],
    "medium": [],
    "weak_or_missing": []
  },
  "forced_or_generic_signals": [],
  "skill_gaps": [],
  "wording_gaps": [],
  "top_fixes": [],
  "strengths": []
}
"""

        user_prompt = f"""
JOB DESCRIPTION
{job_description}

RESUME TEXT
{resume_text}

HEURISTIC ANALYSIS FROM PRE-CHECKS
{json.dumps(heuristic, indent=2)}

Evaluate the resume strictly. Do not inflate score.
If must-haves appear mostly in summary/skills but not in experience, lower the score.
If wording sounds generic or forced, lower recruiter confidence.
Return only JSON.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=3200,
            temperature=0.2,
        )

        content = response.choices[0].message.content or ""

        if "```json" in content:
            content = content.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0]

        try:
            result = json.loads(content.strip())
        except json.JSONDecodeError:
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
                "strengths": []
            }

        # Blend LLM result with stricter heuristic adjustments
        result = self._apply_post_score_adjustments(result, heuristic)
        return result

    def get_improvement_summary(self, score_result: dict) -> str:
        parts = []
        score = score_result.get("score", 0)
        parts.append(f"STRICT ATS SCORE: {score}/100")
        parts.append(f"ATS CONFIDENCE: {score_result.get('ats_confidence', 'unknown')}")
        parts.append(f"RECRUITER CONFIDENCE: {score_result.get('recruiter_confidence', 'unknown')}")

        breakdown = score_result.get("breakdown", {})
        if breakdown:
            parts.append("BREAKDOWN:")
            for key, val in breakdown.items():
                if isinstance(val, dict):
                    parts.append(f"  - {key}: {val.get('score', 0)}/{val.get('max', 0)} | {val.get('details', '')}")

        if score_result.get("forced_or_generic_signals"):
            parts.append("GENERIC / FORCED SIGNALS:")
            for item in score_result["forced_or_generic_signals"][:7]:
                parts.append(f"  - {item}")

        if score_result.get("skill_gaps"):
            parts.append("SKILL GAPS:")
            for item in score_result["skill_gaps"][:7]:
                parts.append(f"  - {item}")

        if score_result.get("wording_gaps"):
            parts.append("WORDING GAPS:")
            for item in score_result["wording_gaps"][:7]:
                parts.append(f"  - {item}")

        if score_result.get("top_fixes"):
            parts.append("TOP FIXES:")
            for i, item in enumerate(score_result["top_fixes"][:8], 1):
                parts.append(f"  {i}. {item}")

        if score_result.get("strengths"):
            parts.append("STRENGTHS:")
            for item in score_result["strengths"][:5]:
                parts.append(f"  - {item}")

        return "\n".join(parts)

    # ---------- Resume formatting ----------

    def _format_resume_for_review(self, resume_content: dict) -> str:
        sections: List[str] = []

        if "summary" in resume_content:
            sections.append("## SUMMARY")
            summary = resume_content["summary"]
            if isinstance(summary, list):
                for bullet in summary:
                    sections.append(f"• {bullet}")
            else:
                sections.append(str(summary))

        if "skills" in resume_content:
            sections.append("\n## TECHNICAL SKILLS")
            skills = resume_content["skills"]
            if isinstance(skills, dict):
                for category, values in skills.items():
                    sections.append(f"{category}: {values}")
            else:
                sections.append(str(skills))

        experience_mapping = {
            "bee_data": "## BEE DATA TECHNOLOGIES",
            "allied_health": "## ALLIED HEALTH AGENCY",
            "byjus": "## BYJU'S",
            "cognizant": "## COGNIZANT",
        }

        for key, header in experience_mapping.items():
            if key in resume_content:
                sections.append(f"\n{header}")
                items = resume_content[key]
                if isinstance(items, list):
                    for bullet in items:
                        sections.append(f"• {bullet}")
                else:
                    sections.append(str(items))

        return "\n".join(sections)

    def _extract_resume_structure(self, resume_content: dict, resume_text: str) -> dict:
        summary = resume_content.get("summary", [])
        skills = resume_content.get("skills", {})
        experience = {}

        for key in ["bee_data", "allied_health", "byjus", "cognizant"]:
            if key in resume_content:
                bullets = resume_content[key]
                experience[key] = bullets if isinstance(bullets, list) else [str(bullets)]

        return {
            "summary": summary if isinstance(summary, list) else [str(summary)],
            "skills": skills if isinstance(skills, dict) else {"General": str(skills)},
            "experience": experience,
            "resume_text": resume_text,
        }

    # ---------- JD signal extraction ----------

    def _extract_jd_signals(self, job_description: str) -> dict:
        jd_lower = job_description.lower()

        must_have = self._extract_section_bullets(job_description, ["must have", "you have", "requirements"])
        nice_to_have = self._extract_section_bullets(job_description, ["nice if you have", "preferred", "plus", "good to have"])

        tech_candidates = [
            "python", "sql", "aws", "sagemaker", "sagemaker studio", "sagemaker pipelines",
            "model registry", "experiment tracking", "hyperparameter tuning", "batch inference",
            "managed endpoints", "docker", "ecr", "kubernetes", "glue", "redshift", "emr",
            "athena", "lambda", "step functions", "pytorch", "tensorflow", "scikit-learn",
            "xgboost", "openai", "llm", "rag", "iam", "vpc", "encryption", "mlops", "ci/cd",
            "model versioning", "monitoring", "retraining", "feature engineering", "s3"
        ]

        explicit_tech = [t for t in tech_candidates if t in jd_lower]

        return {
            "must_have": must_have,
            "nice_to_have": nice_to_have,
            "explicit_tech": explicit_tech,
            "raw": job_description,
        }

    def _extract_section_bullets(self, text: str, section_names: List[str]) -> List[str]:
        lines = [line.strip("•*- \t") for line in text.splitlines() if line.strip()]
        collected = []
        capture = False
        for line in lines:
            lower = line.lower()
            if any(name in lower for name in section_names):
                capture = True
                continue
            if capture and re.match(r"^[A-Z][A-Za-z ]{1,30}:?$", line) and not line.lower().startswith("experience"):
                capture = False
            if capture:
                collected.append(line)
        return collected

    # ---------- Evidence mapping ----------

    def _build_evidence_map(self, structured_resume: dict, jd_signals: dict) -> dict:
        summary_text = " ".join(structured_resume["summary"]).lower()
        skills_text = " ".join([f"{k} {v}" for k, v in structured_resume["skills"].items()]).lower()
        experience_bullets = []
        for role, bullets in structured_resume["experience"].items():
            for bullet in bullets:
                experience_bullets.append({"role": role, "text": bullet, "lower": bullet.lower()})

        evidence = {}
        for tech in jd_signals["explicit_tech"]:
            summary_hit = tech in summary_text
            skills_hit = tech in skills_text
            exp_hits = [b["text"] for b in experience_bullets if tech in b["lower"]]
            evidence[tech] = {
                "summary": summary_hit,
                "skills": skills_hit,
                "experience_hits": exp_hits,
                "strength": self._evidence_strength(summary_hit, skills_hit, exp_hits),
            }
        return evidence

    def _evidence_strength(self, summary_hit: bool, skills_hit: bool, exp_hits: List[str]) -> str:
        if len(exp_hits) >= 2:
            return "strong"
        if len(exp_hits) == 1:
            return "medium"
        if summary_hit or skills_hit:
            return "weak"
        return "missing"

    # ---------- Heuristic analysis ----------

    def _heuristic_analysis(self, job_description: str, structured_resume: dict, jd_signals: dict, evidence: dict) -> dict:
        resume_text = structured_resume["resume_text"]
        bullets = [b for role_bullets in structured_resume["experience"].values() for b in role_bullets]
        bullet_lowers = [b.lower() for b in bullets]

        generic_hits = self._count_generic_phrases(resume_text)
        unsupported_skills = self._find_unsupported_skills(structured_resume)
        repetitive_starts = self._find_repetitive_bullets(bullets)
        weak_bullets = self._find_weak_bullets(bullets)
        metrics_ratio = self._metrics_ratio(bullets)
        domain_signals = self._domain_consistency(structured_resume)
        evidence_summary = self._summarize_evidence(evidence)
        forced_tool_signals = self._find_forced_tool_signals(bullets, jd_signals["explicit_tech"])
        naturalness = self._naturalness_analysis(bullets)
        role_scope = self._role_scope_balance(structured_resume)
        realism_penalty = self._realism_penalty(
            generic_hits,
            unsupported_skills,
            repetitive_starts,
            forced_tool_signals,
            naturalness,
            role_scope
        )

        return {
            "evidence_summary": evidence_summary,
            "generic_phrase_hits": generic_hits,
            "unsupported_skills": unsupported_skills,
            "repetitive_bullet_starts": repetitive_starts,
            "weak_bullets": weak_bullets,
            "metrics_ratio": metrics_ratio,
            "domain_consistency": domain_signals,
            "forced_tool_signals": forced_tool_signals,
            "naturalness": naturalness,
            "role_scope": role_scope,
            "realism_penalty": realism_penalty,
        }

    def _count_generic_phrases(self, text: str) -> List[str]:
        lower = text.lower()
        return [phrase for phrase in self.generic_phrases if phrase in lower]

    def _find_unsupported_skills(self, structured_resume: dict) -> List[str]:
        """
        Only flag CORE capabilities that are missing from work-history evidence.
        Granular tools like Glue, ECR, IAM, Athena, etc. are allowed to live only in Skills.
        """
        skills_text = []
        for _, values in structured_resume["skills"].items():
            if isinstance(values, str):
                skills_text.extend([s.strip() for s in values.split(",") if s.strip()])

        bullets_text = " ".join(
            bullet.lower()
            for role_bullets in structured_resume["experience"].values()
            for bullet in role_bullets
        )
        summary_text = " ".join(structured_resume["summary"]).lower()

        unsupported = []
        for skill in skills_text:
            normalized = skill.lower().strip()
            if len(normalized) < 3:
                continue

            # Skip granular/supporting tools from unsupported-skill penalties
            if normalized in self.granular_skill_terms:
                continue

            # Only penalize important/core skills if they are unsupported
            is_core = normalized in self.core_capability_terms or any(
                core in normalized for core in self.core_capability_terms
            )
            if not is_core:
                continue

            if normalized not in bullets_text and normalized not in summary_text:
                unsupported.append(skill)

        return unsupported[:12]

    def _find_repetitive_bullets(self, bullets: List[str]) -> Dict[str, int]:
        starts = []
        for bullet in bullets:
            words = bullet.strip().split()
            if words:
                starts.append(words[0].lower())
        counts = Counter(starts)
        return {k: v for k, v in counts.items() if v >= 3}

    def _find_weak_bullets(self, bullets: List[str]) -> List[str]:
        weak = []
        for bullet in bullets:
            lower = bullet.lower()
            has_tool = bool(re.search(r"\b(aws|python|sagemaker|docker|kubernetes|spark|openai|langchain|pytorch|tensorflow|xgboost|scikit-learn)\b", lower))
            has_action = bool(re.search(r"\b(built|designed|implemented|developed|engineered|deployed|trained|configured|automated|created|integrated|optimized)\b", lower))
            has_outcome = bool(re.search(r"\b(improv|reduc|increas|serving|supporting|enabling|achiev|maintain|trigger)\b", lower)) or bool(re.search(r"\d+%|\d[\d,]*\+?", lower))

            if has_tool and has_action and not has_outcome:
                weak.append(bullet)
        return weak[:10]

    def _metrics_ratio(self, bullets: List[str]) -> dict:
        with_metrics = 0
        for bullet in bullets:
            if re.search(r"\d+%|\d[\d,]*\+?|\bms\b|\bsec\b|\bseconds\b|\bminutes\b|\busers\b|\brequests\b", bullet.lower()):
                with_metrics += 1
        total = max(len(bullets), 1)
        return {
            "with_metrics": with_metrics,
            "total_bullets": total,
            "ratio": round(with_metrics / total, 2)
        }

    def _domain_consistency(self, structured_resume: dict) -> dict:
        experience_text = " ".join(
            bullet.lower()
            for role_bullets in structured_resume["experience"].values()
            for bullet in role_bullets
        )

        domains = {
            "ml_platform": ["sagemaker", "model registry", "experiment tracking", "batch inference", "endpoint", "monitoring", "retraining"],
            "data_engineering": ["etl", "spark", "glue", "redshift", "emr", "athena", "warehouse", "pipeline"],
            "llm_genai": ["openai", "llm", "rag", "langchain", "langgraph", "prompt", "vector"],
            "software_backend": ["fastapi", "api", "oauth", "service", "microservice"],
            "security_regulated": ["iam", "vpc", "encryption", "access control", "compliance", "governance"],
        }

        counts = {}
        for domain, keywords in domains.items():
            counts[domain] = sum(1 for kw in keywords if kw in experience_text)

        dominant = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return {"counts": counts, "dominant_domains": dominant[:3]}

    def _summarize_evidence(self, evidence: dict) -> dict:
        strong = [k for k, v in evidence.items() if v["strength"] == "strong"]
        medium = [k for k, v in evidence.items() if v["strength"] == "medium"]
        weak = [k for k, v in evidence.items() if v["strength"] in {"weak", "missing"}]
        return {"strong": strong, "medium": medium, "weak_or_missing": weak}

    def _find_forced_tool_signals(self, bullets: List[str], jd_tech: List[str]) -> List[str]:
        signals = []
        for bullet in bullets:
            lower = bullet.lower()
            tech_hits = [t for t in jd_tech if t in lower]
            if len(tech_hits) >= 4:
                # If many tools but no clear objective/result, likely stuffed
                has_result = bool(re.search(r"\d+%|\d[\d,]*\+?|\bimprov|\breduc|\bincreas|\bserving|\bmaintain|\btrigger", lower))
                if not has_result:
                    signals.append(bullet)
        return signals[:8]

    def _realism_penalty(
        self,
        generic_hits: List[str],
        unsupported_skills: List[str],
        repetitive_starts: Dict[str, int],
        forced_tool_signals: List[str],
        naturalness: dict,
        role_scope: dict,
    ) -> int:
        penalty = 0
        penalty += min(len(generic_hits), 6) * 2
        penalty += min(len(unsupported_skills), 6) * 2
        penalty += sum(max(v - 2, 0) for v in repetitive_starts.values())
        penalty += len(forced_tool_signals) * 3
        penalty += len(naturalness.get("vague", [])) * 1
        penalty += len(naturalness.get("overloaded", [])) * 2
        penalty += len([r for r, d in role_scope.items() if d.get("too_broad")]) * 2
        penalty -= min(len(naturalness.get("realistic", [])), 4)  # reward grounded bullets a bit
        return max(0, min(penalty, 24))


    def _naturalness_analysis(self, bullets: List[str]) -> dict:
        templated = []
        vague = []
        realistic = []
        overloaded = []

        for bullet in bullets:
            lower = bullet.lower().strip()

            weak_hits = sum(1 for pat in self.weak_claim_patterns if re.search(pat, lower))
            workflow_hits = 0
            for _, kws in self.real_workflow_signals.items():
                workflow_hits += sum(1 for kw in kws if kw in lower)
            object_hits = sum(1 for term in self.concrete_object_terms if term in lower)
            tool_hits = len(re.findall(r"\b(aws|sagemaker|docker|kubernetes|ecr|glue|athena|emr|lambda|fastapi|openai|langchain|pytorch|tensorflow|xgboost|scikit-learn|spark|sql)\b", lower))
            metric_hits = len(re.findall(r"\d+%|\d[\d,]*\+?|\bms\b|\bsec\b|\bseconds\b|\bminutes\b|\busers\b|\brequests\b", lower))

            if weak_hits >= 1 and workflow_hits == 0 and metric_hits == 0:
                vague.append(bullet)

            if tool_hits >= 4 and object_hits == 0 and metric_hits == 0:
                overloaded.append(bullet)

            if workflow_hits >= 2 and (object_hits >= 1 or metric_hits >= 1):
                realistic.append(bullet)

            # templated: repeated generic patterns or paired verbs without specifics
            if weak_hits >= 1 or re.search(r"\b(designed|built|implemented|developed)\b.+\b(using|with)\b.+\b(enabling|supporting)\b", lower) and object_hits == 0:
                templated.append(bullet)

        total = max(len(bullets), 1)
        natural_score = max(
            0,
            min(
                10,
                round(
                    6
                    + (len(realistic) / total) * 5
                    - (len(vague) / total) * 3
                    - (len(overloaded) / total) * 3
                    - (len(templated) / total) * 2
                )
            ),
        )

        return {
            "templated": templated[:10],
            "vague": vague[:10],
            "realistic": realistic[:10],
            "overloaded": overloaded[:10],
            "naturalness_score": natural_score,
        }

    def _role_scope_balance(self, structured_resume: dict) -> dict:
        """
        Detect roles that try to cover too many disconnected areas at once.
        This reduces credibility even if keywords match.
        """
        role_results = {}
        domain_keywords = {
            "ml_platform": ["sagemaker", "registry", "experiment", "batch inference", "endpoint", "retraining"],
            "llm_apps": ["openai", "rag", "langchain", "langgraph", "prompt", "vector"],
            "backend_api": ["fastapi", "oauth", "api", "service"],
            "data_platform": ["spark", "etl", "warehouse", "glue", "redshift", "athena", "emr"],
            "security": ["iam", "vpc", "encryption", "kms", "access control", "private subnet"],
        }

        for role, bullets in structured_resume["experience"].items():
            text = " ".join(bullets).lower()
            counts = {name: sum(1 for kw in kws if kw in text) for name, kws in domain_keywords.items()}
            active_domains = [name for name, c in counts.items() if c >= 2]
            role_results[role] = {
                "counts": counts,
                "active_domains": active_domains,
                "too_broad": len(active_domains) >= 4
            }

        return role_results

    # ---------- Post adjustments ----------

    def _apply_post_score_adjustments(self, result: dict, heuristic: dict) -> dict:
        score = int(result.get("score", 0))

        # Hard realism deductions
        score -= heuristic.get("realism_penalty", 0)

        # Too many generic phrases
        if len(heuristic.get("generic_phrase_hits", [])) >= 5:
            score -= 4

        naturalness = heuristic.get("naturalness", {})
        if naturalness.get("naturalness_score", 10) <= 4:
            score -= 6
        elif naturalness.get("naturalness_score", 10) <= 6:
            score -= 3

        # If must-have evidence is mostly weak, cap inflated score
        evidence_summary = heuristic.get("evidence_summary", {})
        strong_count = len(evidence_summary.get("strong", []))
        weak_count = len(evidence_summary.get("weak_or_missing", []))
        if strong_count <= 4 and weak_count >= 6:
            score = min(score, 82)

        # If many CORE skills appear unsupported, cap score.
        # Do not overreact to granular tools that only appear in Skills.
        unsupported_count = len(heuristic.get("unsupported_skills", []))
        if unsupported_count >= 6:
            score = min(score, 84)
        elif unsupported_count >= 4:
            score = min(score, 87)

        # If wording is weak and bullets are vague, reduce recruiter confidence
        recruiter_conf = result.get("recruiter_confidence", "medium")
        if heuristic.get("weak_bullets") or heuristic.get("forced_tool_signals") or heuristic.get("naturalness", {}).get("vague"):
            recruiter_conf = "medium" if recruiter_conf == "high" else "low"

        if heuristic.get("naturalness", {}).get("realistic") and not heuristic.get("naturalness", {}).get("overloaded"):
            if recruiter_conf == "low":
                recruiter_conf = "medium"

        # Low metrics presence reduces confidence
        metrics_ratio = heuristic.get("metrics_ratio", {}).get("ratio", 0)
        if metrics_ratio < 0.2:
            score -= 3

        score = max(0, min(score, 100))
        result["score"] = score
        result["passed"] = score >= 85
        result["recruiter_confidence"] = recruiter_conf

        # Merge heuristic findings into output
        forced = result.get("forced_or_generic_signals", [])
        for phrase in heuristic.get("generic_phrase_hits", [])[:6]:
            forced.append(f"Generic phrase used: {phrase}")
        for item in heuristic.get("forced_tool_signals", [])[:4]:
            forced.append(f"Tool-stacked bullet may feel forced: {item}")
        for item in heuristic.get("naturalness", {}).get("overloaded", [])[:4]:
            forced.append(f"Overloaded bullet without enough grounding: {item}")
        for role, data in heuristic.get("role_scope", {}).items():
            if data.get("too_broad"):
                forced.append(f"Role scope may feel too broad for credibility: {role}")

        result["forced_or_generic_signals"] = forced[:12]

        wording_gaps = result.get("wording_gaps", [])
        if heuristic.get("repetitive_bullet_starts"):
            wording_gaps.append(
                "Repeated bullet openings reduce natural tone: "
                + ", ".join(f"{k} ({v}x)" for k, v in heuristic["repetitive_bullet_starts"].items())
            )
        if heuristic.get("weak_bullets"):
            wording_gaps.append("Several bullets mention tools and actions but not a concrete outcome.")
        if heuristic.get("naturalness", {}).get("templated"):
            wording_gaps.append("Some bullets follow a templated pattern and need more concrete workflow detail.")
        if heuristic.get("naturalness", {}).get("vague"):
            wording_gaps.append("Some bullets are too vague and need a clearer object, operational step, or result.")
        result["wording_gaps"] = wording_gaps[:10]

        skill_gaps = result.get("skill_gaps", [])
        for skill in heuristic.get("unsupported_skills", [])[:8]:
            skill_gaps.append(f"Core skill not clearly supported by work history: {skill}")
        result["skill_gaps"] = skill_gaps[:12]

        strengths = result.get("strengths", [])
        domain_info = heuristic.get("domain_consistency", {})
        dominant = domain_info.get("dominant_domains", [])
        if dominant:
            strengths.append(
                "Most consistent experience domains: "
                + ", ".join(f"{name} ({count})" for name, count in dominant if count > 0)
            )
        realistic = heuristic.get("naturalness", {}).get("realistic", [])
        if realistic:
            strengths.append("Some bullets already sound grounded and operational rather than keyword-driven.")
        result["strengths"] = strengths[:8]

        top_fixes = result.get("top_fixes", [])
        if heuristic.get("unsupported_skills"):
            top_fixes.append("Keep granular tools in Skills if needed, but make sure the core capabilities for the target JD are supported by believable work bullets.")
        if heuristic.get("generic_phrase_hits"):
            top_fixes.append("Rewrite summary and top bullets to remove generic phrases and make them sound observed, not claimed.")
        if heuristic.get("forced_tool_signals") or heuristic.get("naturalness", {}).get("overloaded"):
            top_fixes.append("Split overloaded bullets. Show what was built, what object or data it operated on, what tool was used, and what result it produced.")
        if heuristic.get("naturalness", {}).get("vague"):
            top_fixes.append("Replace vague bullets with lived-in workflow details such as data source, feature table, endpoint, batch job, alert, retry, or latency target.")
        if heuristic.get("role_scope"):
            broad_roles = [r for r, d in heuristic["role_scope"].items() if d.get("too_broad")]
            if broad_roles:
                top_fixes.append("Reduce role breadth in at least one role. Too many unrelated domains in the same role can make the resume feel inflated.")
        if heuristic.get("metrics_ratio", {}).get("ratio", 0) < 0.25:
            top_fixes.append("Add more grounded outcomes like throughput, latency, cost reduction, coverage, or user volume.")
        result["top_fixes"] = top_fixes[:10]

        return result


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    scorer = ScorerAgent()

    test_jd = """
AWS Data & AI Engineer
Requirements:
- Amazon SageMaker
- SageMaker Pipelines
- Model Registry
- Python
- Docker
- ECR
- EMR
- Lambda
- CI/CD for ML
- monitoring and retraining
"""

    test_resume = {
        "summary": [
            "AI engineer with experience on AWS SageMaker and MLOps workflows.",
            "Built ML training and deployment pipelines on AWS."
        ],
        "skills": {
            "AWS": "SageMaker, Lambda, S3, EMR, ECR",
            "Programming": "Python, SQL",
            "MLOps": "Docker, CI/CD, MLflow"
        },
        "bee_data": [
            "Built SageMaker training jobs and managed model endpoints for production inference.",
            "Implemented SageMaker Pipelines and Model Registry with CI/CD automation.",
            "Built feature engineering pipeline on EMR and Lambda for batch inference."
        ],
        "allied_health": [
            "Developed Python APIs for ML inference and monitored model drift."
        ],
        "byjus": [
            "Built ETL pipelines and trained classification models."
        ],
        "cognizant": [
            "Developed backend Python modules and automated reporting workflows."
        ]
    }

    result = scorer.score_resume(test_jd, test_resume)
    print(json.dumps(result, indent=2))
