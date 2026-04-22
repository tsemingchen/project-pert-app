import os
from functools import lru_cache

import requests
import streamlit as st

from llm import TOP_MOVIES, get_recommendation

st.set_page_config(
    page_title="Cinema Match",
    page_icon="🎬",
    layout="wide",
)


def get_secret(name: str) -> str | None:
    env_value = os.getenv(name)
    if env_value:
        return env_value

    try:
        secret_value = st.secrets.get(name)
        if secret_value:
            return str(secret_value)
    except Exception:
        pass

    return None


def movie_row(tmdb_id: int):
    matches = TOP_MOVIES[TOP_MOVIES["tmdb_id"].astype(int) == int(tmdb_id)]
    if matches.empty:
        return None
    return matches.iloc[0]


@lru_cache(maxsize=256)
def watch_providers(tmdb_id: int):
    tmdb_api_key = get_secret("TMDB_API_KEY")
    if not tmdb_api_key:
        return {
            "items": [],
            "note": "Streaming availability is not connected right now, but you can still open the movie on TMDB for more details.",
        }

    try:
        response = requests.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}/watch/providers",
            params={"api_key": tmdb_api_key},
            timeout=8,
        )
        response.raise_for_status()
        results = response.json().get("results", {})
        region = results.get("US") or next(iter(results.values()), {})

        providers = []
        for mode, bucket in (
            ("Stream", region.get("flatrate", [])),
            ("Rent", region.get("rent", [])),
            ("Buy", region.get("buy", [])),
        ):
            for item in bucket:
                providers.append((item.get("provider_name", "Unknown"), mode))

        deduped = []
        seen = set()
        for provider in providers:
            if provider not in seen:
                seen.add(provider)
                deduped.append(provider)

        if not deduped:
            return {"items": [], "note": "No US watch-provider data was returned for this movie."}
        return {"items": deduped[:10], "note": "Provider data is shown for the US region."}
    except Exception:
        return {"items": [], "note": "Could not fetch watch-provider data right now."}


st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Allura&family=Bodoni+Moda:opsz,wght@6..96,400;6..96,500;6..96,600&family=Inter:wght@400;500;600&display=swap');

      .stApp {
        background:
          radial-gradient(circle at top left, rgba(116, 219, 229, 0.16), transparent 24%),
          radial-gradient(circle at 82% 14%, rgba(223, 195, 139, 0.08), transparent 16%),
          linear-gradient(145deg, #050c11, #08131b 26%, #0d1b24 72%, #071017);
      }

      .block-container {
        max-width: 1180px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
      }

      .hero-card, .section-card, .result-card {
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 22px;
        background:
          linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.008)),
          linear-gradient(180deg, rgba(10,18,24,0.82), rgba(8,13,17,0.96));
        box-shadow: 0 28px 70px rgba(0,0,0,0.34);
        padding: 1.4rem 1.6rem;
      }

      .brand-mark {
        font-family: "Allura", cursive;
        font-size: 2.2rem;
        color: #dfc38b;
        line-height: 1;
      }

      .hero-accent, .section-kicker {
        color: #74dbe5;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-size: 0.72rem;
      }

      .hero-title, .result-title {
        font-family: "Bodoni Moda", Georgia, serif;
        color: #f4f9fb;
        letter-spacing: -0.04em;
        line-height: 0.95;
      }

      .hero-title {
        font-size: clamp(2.8rem, 5vw, 4.7rem);
        margin: 0.6rem 0 0.35rem 0;
      }

      .hero-copy {
        color: #a8b7bd;
        font-family: "Inter", sans-serif;
        font-size: 0.98rem;
      }

      .match-banner {
        display: inline-block;
        padding: 0.55rem 0.9rem;
        border-radius: 999px;
        border: 1px solid rgba(223,195,139,0.2);
        background: rgba(223,195,139,0.12);
        color: #f6e7c2;
        font-size: 0.88rem;
      }

      .gift-box {
        padding: 1rem 1.1rem;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(223,195,139,0.08), rgba(255,255,255,0.02));
        border: 1px solid rgba(223,195,139,0.14);
      }

      .gift-label {
        display: block;
        color: #dfc38b;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-size: 0.68rem;
        margin-bottom: 0.55rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="hero-card">
      <div class="brand-mark">Cinema Match</div>
      <div class="hero-accent">cinema, curated</div>
      <div class="hero-title">Find better movies.</div>
      <div class="hero-copy">Try: "something like Zendaya sci-fi", "funny feel-good movie", or "Tom Cruise action".</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='height: 0.9rem;'></div>", unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-kicker">Search</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="result-title" style="font-size:2rem; margin-bottom:0.7rem;">Describe what you want to watch</div>',
        unsafe_allow_html=True,
    )

    with st.form("recommendation_form"):
        preferences = st.text_area(
            "What do you want to watch?",
            placeholder="Dark sci-fi with a strong lead, or maybe something with Florence Pugh...",
            height=120,
        )
        history_text = st.text_input(
            "What have you already seen?",
            placeholder="Comma-separated titles, like Inception, Up, The Dark Knight Rises",
        )
        submitted = st.form_submit_button("Let's Find Out")
    st.markdown("</div>", unsafe_allow_html=True)


if submitted:
    history = [item.strip() for item in history_text.split(",") if item.strip()]

    if not preferences.strip():
        st.error("Please enter your movie preferences first.")
    elif not get_secret("OLLAMA_API_KEY"):
        st.error("The app is not connected to an Ollama API key yet.")
        st.info(
            "Local run: set `OLLAMA_API_KEY` in Terminal before starting Streamlit. "
            "Streamlit Cloud: add `OLLAMA_API_KEY` in App Settings > Secrets."
        )
    else:
        with st.spinner("Finding your match..."):
            os.environ["OLLAMA_API_KEY"] = get_secret("OLLAMA_API_KEY") or ""
            tmdb_secret = get_secret("TMDB_API_KEY")
            if tmdb_secret:
                os.environ["TMDB_API_KEY"] = tmdb_secret
            recommendation = get_recommendation(preferences.strip(), history)

        row = movie_row(int(recommendation["tmdb_id"]))
        if row is None:
            st.error("Movie not found in the dataset.")
        else:
            title = str(row.get("title", "Unknown title"))
            poster = str(row.get("poster_path") or "https://placehold.co/600x900/0a0f1f/e8f5ff?text=No+Poster")
            tmdb_url = str(row.get("tmdb_url", "#"))
            providers = watch_providers(int(recommendation["tmdb_id"]))

            left, right = st.columns([0.95, 1.35], gap="large")

            with left:
                st.image(poster, use_container_width=True)

            with right:
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                st.markdown('<div class="match-banner">Congratulations, you have been matched.</div>', unsafe_allow_html=True)
                st.markdown('<div style="height: 0.9rem;"></div>', unsafe_allow_html=True)
                st.markdown('<div class="section-kicker">Movie Match</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="result-title" style="font-size:3.2rem;">{title}</div>', unsafe_allow_html=True)
                st.caption(f"{row.get('year', '')} · {row.get('genres', 'Unknown genres')}")
                st.markdown(
                    '<div class="gift-box">'
                    '<span class="gift-label">Why you got this match</span>'
                    f'{recommendation.get("description", "")}'
                    '</div>',
                    unsafe_allow_html=True,
                )

                meta_left, meta_right = st.columns(2)
                meta_left.markdown("**Top Cast**")
                meta_left.write(str(row.get("top_cast", "Unknown cast")))
                meta_right.markdown("**Director**")
                meta_right.write(str(row.get("director", "Unknown director")))

                st.markdown("**Where To Watch**")
                if providers["items"]:
                    for name, mode in providers["items"]:
                        st.write(f"- {name} ({mode})")
                else:
                    st.write("Streaming details unavailable.")
                st.caption(providers["note"])

                st.markdown(f"[Open on TMDB]({tmdb_url})")

                with st.expander("Movie overview"):
                    st.write(str(row.get("overview", "")))

                st.caption(f"TMDB ID: {int(recommendation['tmdb_id'])}")
                st.markdown("</div>", unsafe_allow_html=True)
