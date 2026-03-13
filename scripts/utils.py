#!/usr/bin/env python3
"""
Shared Utility Functions

Common helpers used across pipeline_runner.py, bucket_generators.py, and other
scripts. Centralises JSON extraction, Gemini API calls, slug generation, and
text-language detection so each module does not need its own copy.

Usage:
    from utils import extract_json_from_llm, call_gemini, topic_slug, is_cyrillic
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import client_config
from client_config import get_api_key


# ── JSON extraction ───────────────────────────────────────────────────────────

def extract_json_from_llm(text: str):
    """Extract the first JSON array or object from LLM response text.

    Handles markdown code fences (```json ... ```) as well as raw JSON.
    Returns the parsed Python object (list or dict).

    Raises:
        ValueError: If no valid JSON array/object is found in the text.
    """
    # Try fenced code block first
    match = re.search(r"```(?:json)?\s*([\[\{][\s\S]*?[\]\}])\s*```", text)
    if match:
        return json.loads(match.group(1))
    # Try raw JSON
    match = re.search(r"([\[\{][\s\S]*[\]\}])", text)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"No valid JSON found in response:\n{text[:400]}")


# ── Gemini API ────────────────────────────────────────────────────────────────

def call_gemini(prompt: str, model: str = "gemini-2.0-flash", client_id: str = None) -> str:
    """Call Gemini API and return the text response.

    Tries the new ``google-genai`` SDK first, then falls back to the older
    ``google-generativeai`` package.

    Args:
        prompt: The text prompt to send.
        model: Gemini model name (default ``gemini-2.0-flash``).
        client_id: Client whose API key to use (default ``bobe``).

    Returns:
        The model's text response.

    Raises:
        ValueError: If no API key is configured.
        ImportError: If neither Gemini SDK is installed.
    """
    api_key = get_api_key(client_id or "bobe", "gemini")
    if not api_key:
        raise ValueError("GOOGLE_AI_API_KEY not set. Check your .env file.")
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text
    except ImportError:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            m = genai.GenerativeModel(model)
            response = m.generate_content(prompt)
            return response.text
        except ImportError:
            raise ImportError(
                "No Gemini SDK found. Install: pip install google-genai"
            )


# ── Slug generation ───────────────────────────────────────────────────────────

def topic_slug(topic: str, max_len: int = 30) -> str:
    """Convert topic text to a filesystem-safe slug.

    Lowercases, truncates to ``max_len`` characters, strips non-alphanumeric
    characters (except spaces), and replaces spaces with underscores.

    Args:
        topic: The topic string to slugify.
        max_len: Maximum character length before cleaning (default 30).

    Returns:
        A safe slug string, or ``"topic"`` if the result would be empty.
    """
    s = topic.lower()[:max_len]
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s or "topic"


# ── Language detection ────────────────────────────────────────────────────────

def is_cyrillic(text: str, threshold: float = 0.3) -> bool:
    """Check whether text contains sufficient Cyrillic characters.

    Useful for validating that a Russian translation actually contains Russian
    script rather than being a pass-through of Latin text.

    Args:
        text: The text to examine.
        threshold: Minimum ratio of Cyrillic letters to total alphabetic
            characters (default 0.3, i.e. 30%).

    Returns:
        True if the Cyrillic ratio meets or exceeds the threshold.
        False if the text contains no alphabetic characters.
    """
    alpha_chars = [ch for ch in text if ch.isalpha()]
    if not alpha_chars:
        return False
    cyrillic_count = sum(1 for ch in alpha_chars if "\u0400" <= ch <= "\u04ff")
    return (cyrillic_count / len(alpha_chars)) >= threshold
