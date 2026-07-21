"""Diagnose the LLM relevance-scoring chain end to end, without Mongo or the API.

Checks, in order:
  1. Ollama is reachable at settings.ollama_host
  2. the configured model is actually pulled
  3. structured outputs work and score_tender() parses the reply
  4. the scores are discriminating (a matching tender must outrank an unrelated one)
  5. how long a full POST /api/tenders/score would take at the current cap

Run:  uv run python -m scripts.check_ollama
Exits non-zero if any check fails, so it doubles as a pre-deploy smoke test.
"""

from __future__ import annotations

import asyncio
import sys
import time

import httpx
from bson import ObjectId

from app.core.config import get_settings
from app.models.enums import ContentType
from app.models.tender import Tender
from app.services.relevance_scorer import score_tender

PROFILE = (
    "Entreprise de BTP basée à Ouagadougou, spécialisée dans les travaux de "
    "voirie, l'assainissement et la construction de bâtiments scolaires. "
    "Capacité: chantiers jusqu'à 500 millions FCFA."
)

RELEVANT = Tender(
    title="Travaux de bitumage de la voirie urbaine de Ouagadougou, secteur 12",
    reference_number="AOO-2026-DEMO-01",
    source_site_id=ObjectId(),
    extraction_type=ContentType.HTML,
    contracting_authority="Ministère des Infrastructures",
    estimated_budget=320_000_000,
    raw_text=(
        "Avis d'appel d'offres ouvert pour les travaux de bitumage et "
        "d'assainissement de la voirie urbaine, lot unique, 12 km de routes "
        "en zone urbaine. Budget estimé 320 000 000 FCFA."
    ),
)

IRRELEVANT = Tender(
    title="Fourniture de licences logicielles de comptabilité et formation des agents",
    reference_number="AOO-2026-DEMO-02",
    source_site_id=ObjectId(),
    extraction_type=ContentType.HTML,
    contracting_authority="Direction des Systèmes d'Information",
    estimated_budget=25_000_000,
    raw_text=(
        "Acquisition de licences d'un progiciel de comptabilité, maintenance "
        "annuelle et formation de 40 agents administratifs. Aucun travaux de "
        "génie civil n'est concerné."
    ),
)


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def fail(msg: str, hint: str = "") -> None:
    print(f"  [FAIL] {msg}")
    if hint:
        print(f"         -> {hint}")


async def main() -> int:
    settings = get_settings()
    print(f"\nOllama host : {settings.ollama_host}")
    print(f"Model       : {settings.ollama_model}")
    print(f"Timeout     : {settings.ollama_timeout_s}s")
    print(f"Score cap   : {settings.score_max_tenders} tenders/appel\n")

    # --- 1 & 2: reachability and model availability -------------------------
    print("1/4  Connexion à Ollama")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.ollama_host}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
    except httpx.HTTPError as exc:
        fail(
            f"injoignable ({exc})",
            "Ollama tourne-t-il ? Lance 'ollama serve', ou vérifie OLLAMA_HOST dans .env",
        )
        return 1
    ok(f"joignable — {len(models)} modèle(s) installé(s)")

    print("\n2/4  Modèle configuré")
    # Ollama reports names tagged ("qwen2.5:1.5b-instruct"); an untagged config
    # value still matches the ":latest" variant, so compare on the base name too.
    base = settings.ollama_model.split(":")[0]
    if settings.ollama_model in models:
        ok(f"'{settings.ollama_model}' est installé")
    elif any(m.split(":")[0] == base for m in models):
        match = next(m for m in models if m.split(":")[0] == base)
        fail(
            f"'{settings.ollama_model}' absent, mais '{match}' existe",
            f"Aligne OLLAMA_MODEL sur '{match}' dans backend/.env, ou pull le tag exact.",
        )
        return 1
    else:
        fail(
            f"'{settings.ollama_model}' n'est pas installé",
            f"Installés: {models or 'aucun'} — lance: ollama pull {settings.ollama_model}",
        )
        return 1

    # --- 3: real scoring calls, parsed by our own service -------------------
    # The very first request also loads the model into RAM (several seconds on
    # CPU). Measuring that would badly overstate the per-tender cost, since a
    # real /score call pays it once and then reuses the loaded model
    # (keep_alive). So: one warm-up, then time the calls that matter.
    print("\n3/4  Scoring réel (structured outputs + parsing)")
    print("       préchauffage du modèle…", flush=True)
    warm_start = time.perf_counter()
    await score_tender(PROFILE, RELEVANT)
    warmup = time.perf_counter() - warm_start
    print(f"       chargement + 1er appel : {warmup:.1f}s (payé une seule fois)")

    started = time.perf_counter()
    hi = await score_tender(PROFILE, RELEVANT)
    hi_time = time.perf_counter() - started
    print(f"       pertinent   -> {hi.label:<12} ({hi_time:.1f}s)  {hi.reason}")

    if hi.label == "indisponible":
        fail(
            "le modèle a répondu quelque chose d'inexploitable",
            "Voir les logs du backend. Le modèle supporte-t-il les structured "
            "outputs ? Essaie un autre modèle (ex. llama3.2:3b).",
        )
        return 1

    started = time.perf_counter()
    lo = await score_tender(PROFILE, IRRELEVANT)
    lo_time = time.perf_counter() - started
    print(f"       hors-sujet  -> {lo.label:<12} ({lo_time:.1f}s)  {lo.reason}")

    elapsed = (hi_time + lo_time) / 2
    ok(f"moyenne à chaud : {elapsed:.1f}s par appel d'offres")

    # --- 4: is the signal actually usable? ----------------------------------
    print("\n4/4  Qualité du signal")
    if hi.label == "correspond" and lo.label == "hors_metier":
        ok("classement parfait : le pertinent est 'correspond', le hors-sujet 'hors_metier'")
    elif hi.score > lo.score:
        ok(f"classement utilisable : '{hi.label}' devant '{lo.label}'")
        print("         Note: pas parfait, mais l'ordre est bon — le tri de la "
              "liste sera correct.")
    else:
        fail(
            f"NON discriminant : pertinent='{hi.label}', hors-sujet='{lo.label}'",
            "Le prompt ne porte pas sur ce modèle. Essaie qwen2.5:3b-instruct "
            "(plus lent mais bien meilleur en français).",
        )
        return 1

    worst_case = elapsed * settings.score_max_tenders
    print(f"\nDurée estimée d'un scoring complet : ~{worst_case:.0f}s "
          f"({settings.score_max_tenders} × {elapsed:.1f}s, séquentiel, modèle déjà chargé)")
    if worst_case > 45:
        fits = max(1, int(45 / elapsed))
        print(f"  Trop long pour une démo en direct. Pour rester sous 45s, mets "
              f"SCORE_MAX_TENDERS={fits} dans backend/.env, ou passe à un modèle "
              f"plus rapide (qwen2.5:0.5b-instruct).")
    else:
        print("  Acceptable pour une démo en direct.")

    print("\nTout est bon — le scoring IA est opérationnel.\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
