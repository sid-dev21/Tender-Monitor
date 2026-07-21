"""LLM-based semantic relevance scoring via a locally hosted Ollama model.

Two-speed principle (CLAUDE.md): AI never runs on the scrape hot path. This
service is called only from an explicit, user-triggered endpoint
(POST /api/tenders/score) over an already keyword-filtered, capped subset of
tenders. The scrape/extraction pipeline is untouched and stays deterministic.

Scoring is intentionally NOT persisted (no new collection, no index, no
migration): each call is a fresh, ephemeral request to Ollama. This keeps the
change additive and low-risk. Caching per (user, tender, profile-hash) is the
natural next step — see README roadmap.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from typing import NamedTuple

import httpx
from loguru import logger

from app.core.config import get_settings
from app.models.tender import Tender


class Relevance(NamedTuple):
    """What the model concluded about one tender.

    `label` is the honest unit: the model picked one of three categories. `score`
    exists only to rank the list — it is derived from `label`, not measured, so
    the UI shows the label and never the number.
    """

    label: str      # "correspond" | "connexe" | "hors_metier" | "indisponible"
    score: int      # ranking key only
    reason: str

_SYSTEM_PROMPT = (
    "Tu es un analyste des marchés publics. On te donne le profil d'une "
    "entreprise et un appel d'offres. Classe l'appel d'offres dans UNE de ces "
    "trois catégories :\n"
    '- "correspond" : ce que demande l\'appel d\'offres est exactement le '
    "métier de l'entreprise.\n"
    '- "connexe" : domaine voisin, l\'entreprise pourrait candidater mais ce '
    "n'est pas son cœur de métier.\n"
    '- "hors_metier" : un autre métier. Exemples : logiciels, informatique, '
    "fournitures de bureau, formation, audit, assurance, transport, "
    "restauration, consultance.\n"
    "Décide d'après ce que l'appel d'offres demande RÉELLEMENT, pas d'après "
    "les compétences de l'entreprise. Une entreprise de BTP face à un marché "
    'de logiciels, c\'est "hors_metier".\n'
    "Justifie en UNE phrase de 15 mots maximum."
)

# Ollama structured outputs constrain decoding to this JSON Schema, rather than
# merely asking for JSON in the prompt.
# https://docs.ollama.com/capabilities/structured-outputs
#
# Why a category and not a 0-100 score: asked for a number, qwen2.5:1.5b
# returned 80-85 for everything, including a software tender it had correctly
# described as software. Producing a calibrated number is a regression task,
# which small models do badly; picking one of three labels is classification,
# which they do well — and `enum` makes the answer structurally impossible to
# get wrong. The numeric score the API exposes is derived here, in code.
_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["correspond", "connexe", "hors_metier"]},
        "reason": {"type": "string", "maxLength": 140},
    },
    "required": ["verdict", "reason"],
}

# Mid-band values: they read as judgements ("90%", "55%", "10%") without
# implying a precision the model does not have.
_VERDICT_SCORES = {"correspond": 90, "connexe": 55, "hors_metier": 10}

# Returned whenever the model is unreachable or answers something unusable. Its
# own label, so the UI can say "unavailable" instead of pretending the tender
# was judged irrelevant. Score 0 keeps such rows at the bottom of the ranking.
_UNAVAILABLE = Relevance(
    "indisponible", 0, "Analyse indisponible (modèle IA injoignable ou réponse invalide)."
)


# Inference is CPU-only in both dev and on the VPS, so prompt length is a direct
# latency cost (every token must be processed before generation starts). The
# discriminating signal lives in the title, authority and first lines of the
# notice — the tail of a long PDF adds tokens, not judgement. 800 chars keeps
# roughly the first paragraph.
_MAX_BODY_CHARS = 800


def _build_prompt(company_profile: str, tender: Tender) -> str:
    """Company profile first, tender last, question last of all.

    The user's keywords are deliberately NOT included. They already did their
    job in the deterministic pre-filter, and feeding them here made a small
    model treat them as evidence found *inside* the notice — it scored an
    unrelated software tender 85/100 while quoting the company's own keywords
    back. Keeping the two layers separate is also the point of the design:
    keywords filter, the model judges meaning.
    """
    profile = company_profile.strip() if company_profile else "(aucun profil renseigné)"
    body = (tender.raw_text or "").strip()
    if len(body) > _MAX_BODY_CHARS:
        body = body[:_MAX_BODY_CHARS] + "…"

    return (
        f"### PROFIL DE L'ENTREPRISE\n{profile}\n\n"
        "### APPEL D'OFFRES À ÉVALUER\n"
        f"Titre : {tender.title}\n"
        f"Autorité contractante : {tender.contracting_authority or 'inconnue'}\n"
        f"Budget estimé : {tender.estimated_budget or 'inconnu'} {tender.currency}\n"
        f"Objet : {body or '(texte indisponible)'}\n\n"
        "### QUESTION\n"
        "Que demande concrètement cet appel d'offres ? Classe-le : "
        '"correspond", "connexe" ou "hors_metier".'
    )


def _parse_response(content: str) -> Relevance:
    """Map the model's verdict onto a Relevance. Never raises."""
    try:
        parsed = json.loads(content)
        verdict = str(parsed["verdict"]).strip().lower()
        reason = str(parsed.get("reason", "")).strip()[:300] or "Aucune justification fournie."
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("relevance_scorer: unparsable Ollama response ({}): {!r}", exc, content[:200])
        return _UNAVAILABLE

    if verdict not in _VERDICT_SCORES:
        # The enum should make this unreachable; if a model ever slips past it,
        # say so rather than silently inventing a verdict.
        logger.warning("relevance_scorer: unexpected verdict {!r}", verdict)
        return _UNAVAILABLE

    return Relevance(verdict, _VERDICT_SCORES[verdict], reason)


# In-memory result cache. A verdict depends only on (this tender, this profile),
# so the same pair never needs a second inference — and on CPU that inference
# costs ~10s. Re-clicking "Scorer avec l'IA" is then instant, which is what makes
# the feature usable in a live demo.
#
# Deliberately process-local and volatile: no new Mongo collection, no index, no
# migration the night before submission. Restarting the API simply re-warms it.
# Persisting per (user, tender, profile) is the natural follow-up.
_CACHE_MAX = 500
_cache: OrderedDict[tuple[str, str], Relevance] = OrderedDict()


def _cache_key(company_profile: str, tender: Tender) -> tuple[str, str]:
    # Hash the profile so editing it invalidates the entries it produced,
    # instead of serving a verdict formed against an outdated description.
    digest = hashlib.sha256(company_profile.encode("utf-8")).hexdigest()[:16]
    return (str(tender.id), digest)


def clear_cache() -> None:
    """Drop every memoized verdict (used by tests; safe to call at any time)."""
    _cache.clear()


async def score_tender(company_profile: str | None, tender: Tender) -> Relevance:
    """Classify one tender against a company profile.

    Never raises: network failures, timeouts, and malformed model output all
    degrade to `_UNAVAILABLE`, so one bad response never breaks the whole
    /api/tenders/score request.
    """
    settings = get_settings()
    profile = company_profile or ""

    # Only tenders already persisted have an id worth caching on.
    key = _cache_key(profile, tender) if tender.id else None
    if key is not None and key in _cache:
        _cache.move_to_end(key)
        return _cache[key]

    prompt = _build_prompt(profile, tender)

    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_s) as client:
            resp = await client.post(
                f"{settings.ollama_host}/api/chat",
                json={
                    "model": settings.ollama_model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "format": _RESPONSE_SCHEMA,
                    "stream": False,
                    # Reasoning models (Qwen3 and friends) emit a long internal
                    # monologue before answering. That is pure cost here: the
                    # task is a three-way classification, and on CPU those
                    # tokens can multiply latency several times over. Models
                    # without a thinking mode ignore this field.
                    "think": False,
                    # keep_alive: hold the model in RAM between tenders — a
                    # /score call is a burst of sequential requests, and paying
                    # the multi-second load on each one would dominate the total.
                    "keep_alive": "10m",
                    "options": {
                        "temperature": 0.1,
                        # A score plus a 15-word sentence is ~45 tokens. Small
                        # models ramble well past that if allowed, and on CPU
                        # every extra token is real wall-clock time.
                        "num_predict": 70,
                    },
                },
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logger.warning("relevance_scorer: Ollama call failed for tender {}: {}", tender.id, exc)
        return _UNAVAILABLE

    result = _parse_response(content)

    # Never memoize a failure: Ollama being down for one request must not stick
    # a permanent "indisponible" on that tender.
    if key is not None and result.label != "indisponible":
        _cache[key] = result
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)

    return result
