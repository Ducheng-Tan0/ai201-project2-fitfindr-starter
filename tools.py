"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""


import os
from dotenv import load_dotenv
from groq import Groq
from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Scoring priority:
      - Title keyword match:       3 points per keyword
      - Style_tags keyword match:  2 points per keyword
      - Description keyword match: 1 point per keyword

    Size matching priority (highest to lowest):
      1. Exact match         (e.g. "M" == "M")
      2. Contains match      (e.g. "M" in "S/M" or "M/L")
      3. One Size            (always last resort)

    Returns:
        List of matching listing dicts sorted by relevance score descending.
        Returns empty list if nothing matches — does NOT raise an exception.
    """
    all_listings = load_listings()

    # ── Step 1: Filter by max_price ───────────────────────────────────────────
    if max_price is not None:
        all_listings = [
            item for item in all_listings
            if item["price"] <= max_price
        ]

    # ── Step 2: Filter by size ────────────────────────────────────────────────
    if size is not None:
        size_lower = size.lower().strip()

        exact        = []  # priority 1 — "M" == "M"
        contains     = []  # priority 2 — "M" in "S/M" or "M/L"
        one_size     = []  # priority 3 — "One Size" listings

        for item in all_listings:
            item_size = item.get("size", "").lower().strip()

            if item_size == size_lower:
                exact.append(item)
            elif "one size" in item_size:
                one_size.append(item)
            elif size_lower in item_size:
                contains.append(item)
            # Items that don't match at all are dropped

        # Combine in priority order for scoring
        all_listings = exact + contains + one_size

    # ── Step 3: Score by keyword overlap ─────────────────────────────────────
    # Split description into individual lowercase keywords
    keywords = [kw.lower().strip() for kw in description.split() if kw.strip()]

    scored = []

    for item in all_listings:
        score = 0

        title_lower    = item.get("title", "").lower()
        desc_lower     = item.get("description", "").lower()
        tags_lower     = [t.lower() for t in item.get("style_tags", [])]

        for kw in keywords:
            # Title match — highest weight
            if kw in title_lower:
                score += 3

            # Style tags match — medium weight
            for tag in tags_lower:
                if kw in tag:
                    score += 2
                    break  # only count once per keyword across all tags

            # Description match — lowest weight
            if kw in desc_lower:
                score += 1

        scored.append((score, item))

    # ── Step 4: Drop zero-score listings ─────────────────────────────────────
    scored = [(score, item) for score, item in scored if score > 0]

    # ── Step 5: Sort by score descending ─────────────────────────────────────
    scored.sort(key=lambda x: x[0], reverse=True)

    return [item for score, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1-2 complete outfits.

    If wardrobe is empty, returns general styling advice for the item.
    Never raises an exception or returns an empty string.
    """
    client = _get_groq_client()

    item_summary = (
        f"Item: {new_item.get('title', 'Unknown item')}\n"
        f"Category: {new_item.get('category', 'unknown')}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Condition: {new_item.get('condition', 'unknown')}\n"
        f"Description: {new_item.get('description', '')}"
    )

    wardrobe_items = wardrobe.get("items", [])

    # ── Empty wardrobe path ───────────────────────────────────────────────────
    if not wardrobe_items:
        prompt = f"""You are a thrift fashion stylist. A user is considering 
buying the following secondhand item but has not shared their wardrobe.

{item_summary}

Give them 1-2 outfit ideas for this item. Suggest what kinds of pieces 
would pair well with it (e.g. "pair with wide-leg jeans and chunky sneakers"). 
Be specific about silhouette, colors, and vibe. Keep it casual and 
conversational — like advice from a stylish friend, not a product description.
Write 3-5 sentences."""

    # ── Wardrobe available path ───────────────────────────────────────────────
    else:
        # Format each wardrobe item as a readable line
        wardrobe_lines = []
        for w in wardrobe_items:
            notes = f" ({w['notes']})" if w.get("notes") else ""
            wardrobe_lines.append(
                f"- {w['name']} "
                f"[{w['category']}] "
                f"colors: {', '.join(w.get('colors', []))} "
                f"| tags: {', '.join(w.get('style_tags', []))}"
                f"{notes}"
            )

        wardrobe_summary = "\n".join(wardrobe_lines)

        prompt = f"""You are a thrift fashion stylist. A user is considering 
buying the following secondhand item.

NEW ITEM:
{item_summary}

THEIR CURRENT WARDROBE:
{wardrobe_summary}

Suggest 1-2 complete outfit combinations using the new item paired with 
specific pieces from their wardrobe above. Name the exact wardrobe pieces 
you are combining. Be specific about how to wear it — tucked or untucked, 
layered or not, what shoes from their wardrobe to pair with. 
Keep the tone casual and conversational. Write 4-6 sentences."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a knowledgeable thrift fashion stylist. "
                    "Give practical, specific outfit advice. "
                    "Never say you cannot help."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=300
    )

    result = response.choices[0].message.content.strip()

    # Safety check — should never be empty given the system prompt
    # but guard just in case
    if not result:
        return (
            f"This {new_item.get('title', 'item')} would work well styled "
            f"with classic basics. Try pairing it with straight-leg jeans "
            f"and clean sneakers for an easy everyday look."
        )

    return result


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Returns a 2-4 sentence Instagram/TikTok style caption.
    If outfit is empty, returns a descriptive error message string.
    Never raises an exception.
    """

    # ── Guard against empty outfit ────────────────────────────────────────────
    if not outfit or not outfit.strip():
        return (
            "Unable to generate a fit card — "
            "no outfit suggestion was provided."
        )

    title    = new_item.get("title", "this thrifted find")
    price    = new_item.get("price", "")
    platform = new_item.get("platform", "a thrift app")
    colors   = ", ".join(new_item.get("colors", []))
    tags     = ", ".join(new_item.get("style_tags", []))

    price_str = f"${price:.2f}" if isinstance(price, float) else str(price)

    prompt = f"""You are writing an Instagram or TikTok caption for a thrift outfit post.

THRIFTED ITEM:
- Name: {title}
- Price: {price_str}
- Platform: {platform}
- Colors: {colors}
- Vibe: {tags}

OUTFIT:
{outfit}

Write a 2-4 sentence caption that:
- Sounds like a real person posting their OOTD — casual, enthusiastic, authentic
- Mentions the item name, price, and platform naturally (each once only)
- Captures the specific vibe of the outfit in concrete terms
- Uses 1-2 relevant emojis maximum
- Does NOT sound like a product description or advertisement

Write only the caption. No intro, no explanation."""

    client = _get_groq_client()

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write short, authentic social media captions "
                    "for thrift outfit posts. Keep it real and specific."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.9,   # high temperature = varied output each time
        max_tokens=150
    )

    return response.choices[0].message.content.strip()


# ── Tool 4: expected_budget ───────────────────────────────────────────────────

def expected_budget(budget: float) -> list[dict] | str:
    """
    Given a budget, find a combination of listings whose total price
    falls within +/- $10 of that budget.

    Args:
        budget (float): The user's total spending target.

    Returns:
        A list of listing dicts whose combined price is within
        budget - 10 and budget + 10 (inclusive).
        Returns an informative string message if no valid combination
        exists — does NOT raise an exception.
    """
    all_listings = load_listings()

    lower = budget - 10
    upper = budget + 10

    # ── Edge case: budget too low for any single item ─────────────────────────
    cheapest = min(all_listings, key=lambda x: x["price"])
    if cheapest["price"] > upper:
        return (
            f"No items are available within your budget range "
            f"(${lower:.2f}–${upper:.2f}). "
            f"The cheapest item is ${cheapest['price']:.2f}. "
            f"Try a higher budget."
        )

    # ── Edge case: budget so large everything fits ────────────────────────────
    total_all = sum(item["price"] for item in all_listings)
    if lower <= total_all <= upper:
        return all_listings

    if total_all < lower:
        return (
            f"Your budget of ${budget:.2f} is large enough to purchase "
            f"everything in the listings "
            f"(total: ${total_all:.2f}). "
            f"Try a lower budget to get a specific combination."
        )

    # ── Find best combination using a greedy approach ─────────────────────────
    # Sort by price ascending so we build up gradually
    sorted_listings = sorted(all_listings, key=lambda x: x["price"])

    best_combo  = []
    best_total  = 0
    best_diff   = float("inf")

    # Try combinations starting from different items
    # to find one whose total lands in [lower, upper]
    for start_idx in range(len(sorted_listings)):
        combo = []
        total = 0

        for item in sorted_listings[start_idx:]:
            if total + item["price"] <= upper:
                combo.append(item)
                total += item["price"]

            # Stop adding once we're in range
            if lower <= total <= upper:
                break

        # Check if this combo lands in range
        if lower <= total <= upper:
            diff = abs(total - budget)
            if diff < best_diff:
                best_combo = combo
                best_total = total
                best_diff  = diff

    # ── Return result ─────────────────────────────────────────────────────────
    if best_combo:
        return best_combo

    return (
        f"Could not find a combination of items that totals "
        f"within ${lower:.2f}–${upper:.2f}. "
        f"Try adjusting your budget by $10-20."
    )


# ── Manual tests ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe