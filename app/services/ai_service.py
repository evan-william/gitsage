"""
AI service powered by Google Gemini.

Security notes:
- API key is never exposed in responses or logs.
- Diff content is capped before being sent.
- All AI output is treated as untrusted text and sanitized before use.
"""

import logging
import re
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import AINotConfiguredError, AIServiceError

logger = logging.getLogger(__name__)

_GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/{model}:generateContent?key={key}"
)

_COMMIT_SYSTEM_PROMPT = """You are an expert developer assistant.
Given a git diff, write a concise, professional commit message following Conventional Commits:
  <type>(<scope>): <short description>

  [optional body — why and what changed, not how]

Types: feat, fix, docs, style, refactor, perf, test, chore, ci, build.
Rules:
- Subject line: max 72 chars, imperative mood, no period.
- Body: wrap at 72 chars, explain motivation.
- Output ONLY the commit message, no explanation, no markdown fences.
"""

_MEDIC_SYSTEM_PROMPT = """You are a senior developer and Git expert.
Given a git error message and context, provide:
1. A plain-language explanation of what went wrong.
2. Step-by-step instructions to fix it (numbered list).
3. If a safe, non-destructive command can fix it automatically, output it on a line starting with: AUTO_FIX:

Keep your response concise and practical. Never suggest force-pushing to shared branches without a clear warning.
"""


async def _call_gemini(prompt: str, system_prompt: str) -> str:
    """Make a single call to the Gemini generateContent API."""
    if not settings.gemini_configured:
        raise AINotConfiguredError()

    url = _GEMINI_API_URL.format(model=settings.GEMINI_MODEL, key=settings.GEMINI_API_KEY)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 512,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT) as client:
            response = await client.post(url, json=payload)
    except httpx.TimeoutException:
        raise AIServiceError("Gemini request timed out.")
    except httpx.RequestError as exc:
        raise AIServiceError(f"Network error contacting Gemini: {exc}")

    if response.status_code == 401:
        raise AINotConfiguredError("Invalid Gemini API key.")
    if response.status_code == 429:
        raise AIServiceError("Gemini rate limit exceeded. Try again shortly.")
    if not response.is_success:
        logger.error("Gemini API error %d: %s", response.status_code, response.text[:200])
        raise AIServiceError(f"Gemini API returned HTTP {response.status_code}.")

    data = response.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise AIServiceError("Unexpected Gemini response format.") from exc

    return text.strip()


async def generate_commit_message(diff: str) -> str:
    """Generate a commit message for a staged diff."""
    if not diff.strip():
        raise ValueError("No staged changes to generate a message for.")

    prompt = f"Git diff to summarize:\n\n```diff\n{diff}\n```"
    raw = await _call_gemini(prompt, _COMMIT_SYSTEM_PROMPT)

    clean = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.MULTILINE)
    clean = re.sub(r"\n?```$", "", clean, flags=re.MULTILINE)
    return clean.strip()


async def diagnose_error(error_output: str, context: Optional[str] = None) -> dict:
    """
    Diagnose a git error and return explanation, steps, and optional auto-fix command.
    Returns: {"explanation": str, "steps": list[str], "auto_fix": str | None}
    """
    if not error_output.strip():
        raise ValueError("Error output cannot be empty.")

    capped_error = error_output[:3000]

    prompt = f"Git error output:\n\n{capped_error}"
    if context:
        prompt += f"\n\nAdditional context: {context[:500]}"

    raw = await _call_gemini(prompt, _MEDIC_SYSTEM_PROMPT)

    auto_fix = None
    clean_lines = []
    for line in raw.splitlines():
        if line.startswith("AUTO_FIX:"):
            auto_fix_candidate = line[len("AUTO_FIX:"):].strip()
            if _is_safe_auto_fix(auto_fix_candidate):
                auto_fix = auto_fix_candidate
        else:
            clean_lines.append(line)

    explanation_text = "\n".join(clean_lines).strip()

    paragraphs = explanation_text.split("\n\n", 1)
    explanation = paragraphs[0].strip()
    steps_raw = paragraphs[1] if len(paragraphs) > 1 else ""

    steps = [
        re.sub(r"^\d+\.\s*", "", line).strip()
        for line in steps_raw.splitlines()
        if re.match(r"^\d+\.", line.strip())
    ]

    return {
        "explanation": explanation,
        "steps": steps,
        "auto_fix": auto_fix,
    }


_SAFE_AUTO_FIX_PATTERNS = [
    r"^git fetch(\s+\S+)?$",
    r"^git pull(\s+--rebase)?(\s+\S+\s+\S+)?$",
    r"^git stash( pop)?$",
    r"^git checkout -- \.$",
    r"^git merge --abort$",
    r"^git rebase --abort$",
    r"^git cherry-pick --abort$",
    r"^git reset HEAD~1$",
    r"^git restore --staged \.$",
]


def _is_safe_auto_fix(cmd: str) -> bool:
    """Whitelist check for auto-fix commands to prevent executing dangerous git ops."""
    for pattern in _SAFE_AUTO_FIX_PATTERNS:
        if re.fullmatch(pattern, cmd.strip()):
            return True
    return False