"""Detect likely fake candidates by comparing application data against LinkedIn."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from anthropic import Anthropic

from .models import Candidate, FakeDetectionResult, FakeRisk, LinkedInProfile

if TYPE_CHECKING:
    from .config import Config

logger = logging.getLogger(__name__)


def detect_fake(
    candidate: Candidate, linkedin: LinkedInProfile, config: Config
) -> FakeDetectionResult:
    """Analyze whether a candidate is likely fake by comparing application vs LinkedIn."""
    client = Anthropic(api_key=config.anthropic_api_key)

    prompt = f"""You are an expert recruiter screening candidates for fake or fraudulent applications.

Compare this candidate's APPLICATION data against their LINKEDIN profile data and assess whether the candidate appears genuine.

APPLICATION DATA:
- Name: {candidate.name}
- Email: {candidate.email}
- Headline: {candidate.headline}
- Experiences: {candidate.experiences}
- Education: {candidate.educations}
- Skills: {candidate.skills}
- Summary: {candidate.summary}
- LinkedIn URL (provided by candidate): {candidate.linkedin_url or "not provided"}
- Source: {candidate.source}

LINKEDIN PROFILE DATA (from web search):
- Profile found: {linkedin.found}
- LinkedIn URL: {linkedin.url}
- Current title: {linkedin.current_title}
- Current company: {linkedin.current_company}
- Past roles: {json.dumps(linkedin.past_roles)}
- Education: {json.dumps(linkedin.education)}
- Location: {linkedin.location}
- Summary: {linkedin.summary}

EVALUATE THESE RED FLAGS:
1. No LinkedIn profile found at all
2. LinkedIn profile exists but job history doesn't match application
3. Claimed experience/titles seem inflated vs LinkedIn
4. Education claims don't match
5. Profile appears very new or sparse
6. Name/details mismatch between application and LinkedIn
7. Unlikely combination of skills/experience for the claimed role

Return a JSON object:
{{
  "risk_level": "definitely_fake" | "likely_fake" | "uncertain" | "likely_real" | "verified",
  "confidence_score": 0-100 (higher = more confident candidate is REAL),
  "reasons": ["list of specific reasons for your assessment"],
  "details": "1-2 sentence summary of your assessment"
}}

Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model=config.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[: text.rfind("```")]
            text = text.strip()

        data = json.loads(text)
        risk_map = {v.value: v for v in FakeRisk}
        risk_level = risk_map.get(data.get("risk_level", "uncertain"), FakeRisk.UNCERTAIN)

        return FakeDetectionResult(
            risk_level=risk_level,
            confidence_score=data.get("confidence_score", 50),
            reasons=data.get("reasons", []),
            details=data.get("details", ""),
        )
    except Exception as e:
        logger.error("Fake detection failed for %s: %s", candidate.name, e)
        return FakeDetectionResult()
