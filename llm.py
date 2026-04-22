"""
Environment variables used by this file:
- OLLAMA_API_KEY
- TMDB_API_KEY (optional, used by the local web app for watch-provider lookups)
"""

import argparse
import json
import os
import re
import time
from functools import lru_cache
from typing import Iterable

import ollama
import pandas as pd

MODEL = "gemma4:31b-cloud"

DATA_PATH = os.path.join(os.path.dirname(__file__), "tmdb_top1000_movies.csv")
TOP_MOVIES = pd.read_csv(DATA_PATH).copy()

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "but",
    "for",
    "i",
    "if",
    "im",
    "in",
    "into",
    "is",
    "it",
    "its",
    "me",
    "movie",
    "movies",
    "my",
    "of",
    "on",
    "or",
    "something",
    "that",
    "the",
    "their",
    "them",
    "they",
    "to",
    "want",
    "with",
}


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _row_text(row: pd.Series) -> str:
    parts = [
        row.get("title", ""),
        row.get("genres", ""),
        row.get("keywords", ""),
        row.get("overview", ""),
        row.get("tagline", ""),
        row.get("director", ""),
        row.get("top_cast", ""),
    ]
    return " ".join(str(part) for part in parts if pd.notna(part))


def _history_title_tokens(history: Iterable[str]) -> set[str]:
    tokens: set[str] = set()
    for title in history:
        tokens.update(_tokenize(title))
    return tokens


def _phrase_score(preferences: str, field_value: str, weight: float) -> float:
    normalized_preferences = _normalize_text(preferences)
    normalized_field = _normalize_text(field_value)
    if not normalized_preferences or not normalized_field:
        return 0.0

    score = 0.0
    # Reward exact multi-word name or title hits like "Tom Cruise" or "Zendaya".
    for phrase in re.split(r"[,;/]| and | with |\n", normalized_preferences):
        phrase = phrase.strip()
        if len(phrase) >= 4 and phrase in normalized_field:
            score += weight
    return score


def _score_movie(
    row: pd.Series,
    preferences: str,
    preference_tokens: set[str],
    history_tokens: set[str],
) -> float:
    text = _row_text(row).lower()
    score = 0.0

    for token in preference_tokens:
        if token in text:
            score += 3.0

    genre_text = str(row.get("genres", "")).lower()
    keyword_text = str(row.get("keywords", "")).lower()
    overview_text = str(row.get("overview", "")).lower()
    title_text = str(row.get("title", "")).lower()
    cast_text = str(row.get("top_cast", "")).lower()
    director_text = str(row.get("director", "")).lower()

    for token in preference_tokens:
        if token in genre_text:
            score += 4.0
        if token in keyword_text:
            score += 2.5
        if token in overview_text:
            score += 1.5
        if token in cast_text:
            score += 5.0
        if token in director_text:
            score += 5.0
        if token in title_text:
            score += 6.0

    score += _phrase_score(preferences, cast_text, 18.0)
    score += _phrase_score(preferences, director_text, 16.0)
    score += _phrase_score(preferences, title_text, 14.0)

    overlap_with_history = len(_tokenize(str(row.get("title", ""))) & history_tokens)
    score -= overlap_with_history * 2.0

    vote_count = float(row.get("vote_count", 0) or 0)
    vote_average = float(row.get("vote_average", 0) or 0)
    popularity = float(row.get("popularity", 0) or 0)

    score += min(vote_count / 1000.0, 5.0)
    score += vote_average / 10.0
    score += min(popularity / 100.0, 2.0)
    return score


def _candidate_pool(
    preferences: str,
    history: list[str],
    history_ids: list[int],
    limit: int = 12,
) -> pd.DataFrame:
    preference_tokens = _tokenize(preferences)
    history_token_set = _history_title_tokens(history)
    excluded_ids = {int(movie_id) for movie_id in history_ids}

    candidates = TOP_MOVIES[~TOP_MOVIES["tmdb_id"].astype(int).isin(excluded_ids)].copy()
    if candidates.empty:
        return TOP_MOVIES.nlargest(limit, "vote_count").copy()

    candidates["_score"] = candidates.apply(
        lambda row: _score_movie(row, preferences, preference_tokens, history_token_set),
        axis=1,
    )

    ranked = candidates.sort_values(
        by=["_score", "vote_count", "vote_average"], ascending=[False, False, False]
    )
    return ranked.head(limit).copy()


def _build_prompt(preferences: str, history: list[str], candidates: pd.DataFrame) -> str:
    history_text = ", ".join(f'"{title}"' for title in history) if history else "none"
    movie_list = "\n".join(
        (
            f'- tmdb_id={int(row.tmdb_id)} | title="{row.title}" | year={int(row.year)}'
            f' | genres="{row.genres}"'
            f' | top_cast="{str(row.top_cast)[:140]}"'
            f' | director="{str(row.director)[:90]}"'
            f' | overview="{str(row.overview)[:240]}"'
        )
        for row in candidates.itertuples()
    )

    return f"""You are a movie recommendation assistant.

Choose exactly one movie from the candidate list.

User preferences:
{preferences}

Already watched:
{history_text}

Candidate movies:
{movie_list}

Rules:
- Pick exactly one movie from the candidate list.
- Do not recommend anything the user already watched.
- Prefer the best thematic match to the user's request.
- Return valid JSON only.

Response format:
{{
  "tmdb_id": <integer from candidate list>,
  "description": "<short pitch under 500 characters>"
}}"""


@lru_cache(maxsize=1)
def _client() -> ollama.Client:
    api_key = os.getenv("OLLAMA_API_KEY")
    if not api_key:
        raise RuntimeError("OLLAMA_API_KEY is not set.")
    return ollama.Client(
        host="https://ollama.com",
        headers={"Authorization": f"Bearer {api_key}"},
    )


def _extract_json_object(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise json.JSONDecodeError("Empty response", text, 0)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _fallback_recommendation(candidates: pd.DataFrame, preferences: str) -> dict:
    choice = candidates.iloc[0]
    genres = str(choice.get("genres", "this style")).strip()
    overview = str(choice.get("overview", "")).strip()
    base_description = (
        f'{choice["title"]} fits because it leans into {genres.lower()} and matches your request for '
        f'{preferences.strip().rstrip(".")}.'
    )
    if overview:
        base_description += f" {overview[:220].rstrip()}"

    return {
        "tmdb_id": int(choice["tmdb_id"]),
        "description": base_description[:500],
    }


@lru_cache(maxsize=256)
def _fast_recommendation_cached(
    preferences: str,
    history: tuple[str, ...],
    history_ids: tuple[int, ...],
) -> dict:
    candidates = _candidate_pool(preferences, list(history), list(history_ids))
    return _fallback_recommendation(candidates, preferences)


def _normalize_result(
    raw_result: dict,
    candidates: pd.DataFrame,
    preferences: str,
) -> dict:
    valid_ids = set(candidates["tmdb_id"].astype(int))
    fallback = _fallback_recommendation(candidates, preferences)

    try:
        tmdb_id = int(raw_result.get("tmdb_id"))
    except (TypeError, ValueError, AttributeError):
        return fallback

    if tmdb_id not in valid_ids:
        return fallback

    description = str(raw_result.get("description", "")).strip() or fallback["description"]
    return {
        "tmdb_id": tmdb_id,
        "description": description[:500],
    }


def get_recommendation(
    preferences: str, history: list[str], history_ids: list[int] = []
) -> dict:
    """Return a dict with keys 'tmdb_id' (int) and 'description' (str)."""
    candidates = _candidate_pool(preferences, history, history_ids)
    prompt = _build_prompt(preferences, history, candidates)

    try:
        response = _client().chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        raw_result = _extract_json_object(response.message.content)
        return _normalize_result(raw_result, candidates, preferences)
    except Exception:
        return _fallback_recommendation(candidates, preferences)


def get_recommendation_fast(
    preferences: str, history: list[str], history_ids: list[int] = []
) -> dict:
    """Fast deterministic recommendation path for interactive app use."""
    return _fast_recommendation_cached(
        preferences.strip(),
        tuple(history),
        tuple(int(movie_id) for movie_id in history_ids),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a local movie recommendation test."
    )
    parser.add_argument(
        "--preferences",
        type=str,
        help="User preferences text. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--history",
        type=str,
        help='Comma-separated watch history titles. Example: "The Avengers, Up"',
    )
    args = parser.parse_args()

    print("Movie recommender - type your preferences and press Enter.")
    print("For watch history, enter comma-separated movie titles or leave blank.")

    preferences = (
        args.preferences.strip()
        if args.preferences and args.preferences.strip()
        else input("Preferences: ").strip()
    )
    history_raw = (
        args.history.strip()
        if args.history and args.history.strip()
        else input("Watch history (optional): ").strip()
    )
    history = (
        [title.strip() for title in history_raw.split(",") if title.strip()]
        if history_raw
        else []
    )

    print("\nThinking...\n")
    start = time.perf_counter()
    result = get_recommendation(preferences, history)
    print(result)
    elapsed = time.perf_counter() - start

    print(f"\nServed in {elapsed:.2f}s")
