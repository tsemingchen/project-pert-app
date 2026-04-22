# Movie Recommender

## Overview

This project implements `get_recommendation()` in `llm.py` for a movie recommendation agent. The function takes a user's preferences and watch history, ranks candidate movies from the provided TMDB dataset, queries the required `gemma4:31b-cloud` model through Ollama Cloud, and returns one recommendation with a short explanation.

In addition to the assignment logic, this repo also includes a Streamlit demo app in `streamlit_app.py`.

## Approach

The recommender uses a hybrid approach:

1. It loads the provided `tmdb_top1000_movies.csv` file.
2. It scores movies based on:
   - genre overlap
   - keyword overlap
   - overview overlap
   - title matches
   - actor / actress matches from `top_cast`
   - director matches
3. It excludes movies already present in the user's watch history.
4. It selects a ranked candidate pool and sends those candidates to the LLM.
5. It asks the LLM to choose exactly one movie and return JSON in the required format.
6. If the LLM response is malformed or unavailable, the code falls back to the highest-ranked valid candidate so the function still returns a valid result.

This design keeps the recommendation relevant while also being robust enough to satisfy the grading constraints.

## Evaluation Strategy

I evaluated the implementation in two ways:

1. By running the provided `test.py` script to verify:
   - output format
   - valid `tmdb_id`
   - no repeats from watch history
   - time limit compliance
   - requirements coverage

2. By manually testing prompts such as:
   - superhero / action requests
   - actor-name searches like Zendaya
   - character / franchise style searches like Scarlet Witch
   - funny / feel-good requests

## File Guide

- `streamlit_app.py`
  Streamlit web app for interactive demo use.

- `llm.py`
  Main implementation. Contains dataset loading, candidate scoring, prompt construction, LLM call, JSON parsing, and fallback behavior.

- `requirements.txt`
  Python dependencies required to run the submission.

- `tmdb_top1000_movies.csv`
  Dataset used by `llm.py` to rank and select recommendation candidates.

## How To Run

### Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### Set the API key

```bash
export OLLAMA_API_KEY="your_key_here"
```

### Run the assignment test

```bash
python3 test.py
```

### Run a manual example

```bash
python3 llm.py --preferences "something with zendaya sci fi"
```

### Run the Streamlit website

```bash
streamlit run streamlit_app.py
```

If you also want live watch-provider data, optionally set:

```bash
export TMDB_API_KEY="your_tmdb_key_here"
```

## Notes

- The implementation does **not** hard-code the API key.
- It reads `OLLAMA_API_KEY` from the environment as required.
- The required model remains `gemma4:31b-cloud`.
