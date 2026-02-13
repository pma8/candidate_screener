"""LinkedIn profile enrichment via web search (Tavily)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from anthropic import Anthropic

from .models import Candidate, LinkedInProfile

if TYPE_CHECKING:
    from .config import Config

logger = logging.getLogger(__name__)


def _search_linkedin(candidate: Candidate, config: Config) -> str:
    """Search the web for a candidate's LinkedIn profile and return raw results."""
    from tavily import TavilyClient

    client = TavilyClient(api_key=config.tavily_api_key)

    # Build a targeted search query
    parts = [candidate.name]
    if candidate.headline:
        parts.append(candidate.headline)
    elif candidate.experiences:
        # Use first line of experience for better targeting
        first_exp = candidate.experiences.split("\n")[0].strip()
        if first_exp:
            parts.append(first_exp)
    parts.append("LinkedIn")

    query = " ".join(parts)
    logger.info("Searching: %s", query)

    response = client.search(
        query=query,
        max_results=config.search_max_results,
        include_answer=True,
        search_depth="advanced",
    )

    return json.dumps(response, indent=2, default=str)


def _parse_linkedin_with_llm(
    candidate: Candidate, search_results: str, config: Config
) -> LinkedInProfile:
    """Use Claude to extract structured LinkedIn data from search results."""
    client = Anthropic(api_key=config.anthropic_api_key)

    prompt = f"""Analyze these web search results about a job candidate and extract LinkedIn profile information.

CANDIDATE APPLICATION DATA:
- Name: {candidate.name}
- Headline: {candidate.headline}
- Experiences (from application): {candidate.experiences}
- Education (from application): {candidate.educations}
- LinkedIn URL (from application): {candidate.linkedin_url or "not provided"}

WEB SEARCH RESULTS:
{search_results}

Extract and return a JSON object with these fields:
- "found": boolean - whether a matching LinkedIn profile was found
- "url": string - the LinkedIn profile URL if found
- "current_title": string - their current job title per LinkedIn
- "current_company": string - their current company per LinkedIn
- "past_roles": list of strings - past job titles and companies from LinkedIn
- "education": list of strings - education entries from LinkedIn
- "location": string - location per LinkedIn
- "summary": string - brief summary of their LinkedIn profile

If no LinkedIn profile is found or search results are inconclusive, set "found" to false and leave other fields empty.

Return ONLY valid JSON, no other text."""

    response = client.messages.create(
        model=config.model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[: text.rfind("```")]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON for %s", candidate.name)
        return LinkedInProfile(raw_search_results=search_results)

    return LinkedInProfile(
        found=data.get("found", False),
        url=data.get("url", ""),
        current_title=data.get("current_title", ""),
        current_company=data.get("current_company", ""),
        past_roles=data.get("past_roles", []),
        education=data.get("education", []),
        location=data.get("location", ""),
        summary=data.get("summary", ""),
        raw_search_results=search_results,
    )


def enrich_candidate(candidate: Candidate, config: Config) -> LinkedInProfile:
    """Enrich a single candidate with LinkedIn data via web search."""
    if not config.tavily_api_key:
        logger.warning("No Tavily API key configured. Skipping LinkedIn enrichment.")
        return LinkedInProfile()

    try:
        raw_results = _search_linkedin(candidate, config)
        return _parse_linkedin_with_llm(candidate, raw_results, config)
    except Exception as e:
        logger.error("Enrichment failed for %s: %s", candidate.name, e)
        return LinkedInProfile()
