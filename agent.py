"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""


import os
import json
from dotenv import load_dotenv
from groq import Groq
from tools import search_listings, suggest_outfit, create_fit_card

load_dotenv()


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.
    """
    return {
        "query":             query,   # original user query
        "parsed":            {},      # extracted description / size / max_price
        "search_results":    [],      # list of matching listing dicts
        "selected_item":     None,    # top result passed into suggest_outfit
        "wardrobe":          wardrobe,# user's wardrobe dict
        "outfit_suggestion": None,    # string returned by suggest_outfit
        "fit_card":          None,    # string returned by create_fit_card
        "error":             None,    # set if interaction ended early
    }


# ── query parser ──────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Uses the Groq LLM to extract three structured fields from a
    natural language query:
      - description (str): what item the user is looking for
      - size (str or null): size mentioned, or null if not specified
      - max_price (float or null): price ceiling, or null if not specified

    Returns a dict with those three keys.
    Falls back to sensible defaults if parsing fails.
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    prompt = f"""Extract structured search parameters from this thrifting query.

Query: "{query}"

Return ONLY a valid JSON object with exactly these three fields:
{{
  "description": "keywords describing the item (string)",
  "size": "size string or null if not mentioned",
  "max_price": price as a number or null if not mentioned
}}

Rules:
- description should be the item keywords only (e.g. "vintage graphic tee")
- size should be exactly as mentioned (e.g. "M", "S", "L") or null
- max_price should be a number like 30.0 or null
- Return ONLY the JSON object, no explanation, no markdown, no backticks

Examples:
Query: "vintage graphic tee under $30 size M"
Output: {{"description": "vintage graphic tee", "size": "M", "max_price": 30.0}}

Query: "looking for a flannel shirt"
Output: {{"description": "flannel shirt", "size": null, "max_price": null}}

Query: "baggy jeans under fifty bucks"
Output: {{"description": "baggy jeans", "size": null, "max_price": 50.0}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise query parser. "
                        "Return only valid JSON, nothing else."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,  # zero temperature = deterministic parsing
            max_tokens=100
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if the LLM adds them despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)

        # Validate all three keys exist
        return {
            "description": parsed.get("description", query),
            "size":        parsed.get("size", None),
            "max_price":   parsed.get("max_price", None),
        }

    except (json.JSONDecodeError, KeyError, Exception):
        # If parsing fails for any reason, use the full query as description
        # and no size or price filter — safe fallback
        return {
            "description": query,
            "size":        None,
            "max_price":   None,
        }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Returns:
        The session dict. Check session["error"] first — if not None,
        the interaction ended early and fit_card/outfit_suggestion are None.
    """

    # ── Step 1: Initialize session ────────────────────────────────────────────
    session = _new_session(query, wardrobe)

    print(f"\n[Agent] Query received: {query}")

    # ── Step 2: Parse the query ───────────────────────────────────────────────
    print("[Agent] Parsing query...")
    parsed = _parse_query(query)
    session["parsed"] = parsed

    description = parsed["description"]
    size        = parsed["size"]
    max_price   = parsed["max_price"]

    print(f"[Agent] Parsed → description: '{description}' | "
          f"size: {size} | max_price: {max_price}")

    # ── Step 3: Call search_listings ──────────────────────────────────────────
    print("[Agent] Searching listings...")
    results = search_listings(description, size=size, max_price=max_price)
    session["search_results"] = results

    # Branch: if no results, set error and return early
    # Do NOT proceed to suggest_outfit with empty input
    if not results:
        session["error"] = (
            f"No listings found matching '{description}'"
            + (f" in size {size}" if size else "")
            + (f" under ${max_price:.2f}" if max_price else "")
            + ". Try a broader description, a different size, "
              "or a higher budget."
        )
        print(f"[Agent] No results found. Returning early.")
        return session

    print(f"[Agent] Found {len(results)} result(s).")

    # ── Step 4: Select top result ─────────────────────────────────────────────
    session["selected_item"] = results[0]
    print(f"[Agent] Selected: {results[0]['title']} — ${results[0]['price']}")

    # ── Step 5: Call suggest_outfit ───────────────────────────────────────────
    print("[Agent] Generating outfit suggestion...")
    outfit = suggest_outfit(session["selected_item"], session["wardrobe"])
    session["outfit_suggestion"] = outfit
    print("[Agent] Outfit suggestion generated.")

    # ── Step 6: Call create_fit_card ──────────────────────────────────────────
    print("[Agent] Creating fit card...")
    fit_card = create_fit_card(
        session["outfit_suggestion"],
        session["selected_item"]
    )
    session["fit_card"] = fit_card
    print("[Agent] Fit card created.")

    # ── Step 7: Return completed session ─────────────────────────────────────
    print("[Agent] Done.\n")
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    # ── Happy path ────────────────────────────────────────────────────────────
    print("=" * 60)
    print("TEST 1: Happy path — vintage graphic tee")
    print("=" * 60)

    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )

    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"\nSelected item : {session['selected_item']['title']}")
        print(f"Price         : ${session['selected_item']['price']}")
        print(f"Platform      : {session['selected_item']['platform']}")
        print(f"\nOutfit        :\n{session['outfit_suggestion']}")
        print(f"\nFit card      :\n{session['fit_card']}")

        # State verification prints
        print("\n── State verification ──")
        print(f"session['selected_item'] id    : {session['selected_item']['id']}")
        print(f"session['outfit_suggestion'][:50]: "
              f"{session['outfit_suggestion'][:50]}...")
        print(f"session['fit_card'][:50]       : "
              f"{session['fit_card'][:50]}...")
        print(f"session['error']               : {session['error']}")

    # ── No-results path ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("TEST 2: No-results path — impossible query")
    print("=" * 60)

    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )

    print(f"\nError message  : {session2['error']}")
    print(f"fit_card       : {session2['fit_card']}")
    print(f"outfit         : {session2['outfit_suggestion']}")
    print(f"selected_item  : {session2['selected_item']}")

    # Verify branch worked correctly
    assert session2["error"] is not None,  "ERROR: error should be set"
    assert session2["fit_card"] is None,   "ERROR: fit_card should be None"
    assert session2["outfit_suggestion"] is None, \
        "ERROR: outfit_suggestion should be None"
    print("\n✓ No-results branch verified correctly")