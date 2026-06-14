# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

FitFindr is a multi-tool AI agent that helps users find secondhand 
clothing pieces and figure out how to style them. A user describes 
what they are looking for in plain language optionally with a size, 
price ceiling, or total budget  and the agent searches a mock 
listings dataset, suggests complete outfits using the user's wardrobe, 
and generates a shareable social media caption for the find.

## What's Included

```
ai201-project2-fitfindr-starter/

├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── tests/
│   ├── init.py
│   └── test_tools.py          # pytest tests for all four tools
├── utils/
│   └── data_loader.py         # Helper functions for loading data
├── tools.py                   # All four tool implementations
├── agent.py                   # Planning loop and session management
├── app.py                     # Gradio web interface
├── planning.md                # Spec written before implementation
├── conftest.py                # pytest path configuration
├── failure_mode_test.py       # triggers 
└── requirements.txt

```

## Setup

```bash
git clone https://github.com/YOUR-USERNAME/ai201-project2-fitfindr-starter.git
cd ai201-project2-fitfindr-starter
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

---

## Tool Inventory

### Tool 1: search_listings

**Purpose:** Searches the mock listings dataset for items matching 
a description, with optional size and price filters. Returns results 
sorted by relevance score — title matches weighted highest, then 
style tag matches, then description matches.

**Function signature:**
```python
search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None
) -> list[dict]
```

**Inputs:**
- `description` (str): Keywords describing the item 
  (e.g. `"vintage graphic tee"`)
- `size` (str | None): Size to filter by, case-insensitive. 
  Exact matches ranked first, then partial matches like `"S/M"`, 
  then `"One Size"`. Pass `None` to skip size filtering.
- `max_price` (float | None): Maximum price inclusive. 
  Pass `None` to skip price filtering.

**Output:** A list of listing dicts sorted by relevance score 
descending. Each dict contains: `id`, `title`, `description`, 
`category`, `style_tags` (list), `size`, `condition`, `price` 
(float), `colors` (list), `brand`, `platform`. Returns an empty 
list if nothing matches — never raises an exception.

---

### Tool 2: suggest_outfit

**Purpose:** Given a thrifted item and the user's wardrobe, uses 
the Groq LLM to suggest 1–2 complete outfit combinations. If the 
wardrobe is empty, returns general styling advice instead of 
wardrobe-specific combinations.

**Function signature:**
```python
suggest_outfit(
    new_item: dict,
    wardrobe: dict
) -> str
```

**Inputs:**
- `new_item` (dict): A listing dict from `search_listings` 
  (fields: id, title, description, category, style_tags, size, 
  condition, price, colors, brand, platform)
- `wardrobe` (dict): A wardrobe dict with an `"items"` key 
  containing a list of wardrobe item dicts. Each wardrobe item 
  has: `id`, `name`, `category`, `colors` (list), 
  `style_tags` (list), `notes` (str or None). May be empty.

**Output:** A non-empty string with outfit suggestions. 
If the wardrobe is empty, returns general styling advice 
for the item. Never returns an empty string or raises an exception.

---

### Tool 3: create_fit_card

**Purpose:** Generates a short, shareable social media caption 
for a thrifted outfit. Uses the Groq LLM at high temperature 
(0.9) to produce varied output each time.

**Function signature:**
```python
create_fit_card(
    outfit: str,
    new_item: dict
) -> str
```

**Inputs:**
- `outfit` (str): The outfit suggestion string returned by 
  `suggest_outfit()`
- `new_item` (dict): The listing dict for the thrifted item 
  (same structure as `search_listings` output)

**Output:** A 2–4 sentence string written in a casual, 
authentic social media voice. Mentions the item name, price, 
and platform once each. If `outfit` is empty or whitespace-only, 
returns the error string 
`"Unable to generate a fit card — no outfit suggestion was provided."` 
rather than raising an exception.

---

### Tool 4: expected_budget

**Purpose:** Given a total budget, finds a combination of 
listings whose combined price falls within ±$10 of that budget. 
Useful for users who want to spend a specific total rather than 
search for a single item.

**Function signature:**
```python
expected_budget(
    budget: float
) -> list[dict] | str
```

**Inputs:**
- `budget` (float): The user's total spending target in dollars

**Output:** A list of listing dicts whose combined price is 
within `budget - 10` and `budget + 10` inclusive, or an 
informative string message if no valid combination exists 
(budget too low for any item, or budget large enough to 
purchase everything). Never raises an exception.

---

## How the Planning Loop Works

The planning loop in `run_agent()` follows a conditional sequence — 
it does not call all tools unconditionally. Each step checks its 
result before proceeding.

**Step 1 — Initialize session:**
A fresh session dict is created with fields for the query, 
parsed parameters, search results, selected item, wardrobe, 
outfit suggestion, fit card, and error.

**Step 2 — Parse the query:**
The Groq LLM extracts three structured fields from the natural 
language query: `description` (str), `size` (str or None), and 
`max_price` (float or None). Temperature is set to 0.0 for 
deterministic parsing. Output is expected as a JSON object. 
A fallback uses the full query as the description with no 
size or price filters if parsing fails.

**Step 3 — Call search_listings() and branch:**
`search_listings(description, size, max_price)` is called. 
If the result is an empty list, `session["error"]` is set to a 
helpful message and the session is returned immediately. 
`suggest_outfit` and `create_fit_card` are never called with 
empty input. This is the only early-exit branch in the loop.

**Step 4 — Select top result:**
`session["selected_item"]` is set to `results[0]`, the 
highest-scoring match.

**Step 5 — Call suggest_outfit():**
`suggest_outfit(selected_item, wardrobe)` is called. 
The tool handles the empty wardrobe case internally — 
no branching is needed at the planning loop level.

**Step 6 — Call create_fit_card():**
`create_fit_card(outfit_suggestion, selected_item)` is called. 
The tool handles the empty outfit string case internally.

**Step 7 — Return session:**
The completed session dict is returned with all fields populated. 
`session["error"]` is None on success.

---

## State Management

All state for one interaction is stored in a single session dict 
initialized at the start of `run_agent()`. No tool modifies the 
session dict directly — only `run_agent()` reads from and writes 
to it. Tools receive their inputs as function arguments and return 
values, which `run_agent()` then stores in the session.

| Field | Type | Set when | Passed to |
|---|---|---|---|
| `query` | str | Step 1 | Never modified |
| `parsed` | dict | Step 2 | Keys passed as args to search_listings |
| `search_results` | list[dict] | Step 3 | First element becomes selected_item |
| `selected_item` | dict | Step 4 | suggest_outfit, create_fit_card |
| `wardrobe` | dict | Step 1 (from input) | suggest_outfit |
| `outfit_suggestion` | str | Step 5 | create_fit_card |
| `fit_card` | str | Step 6 | Returned to interface |
| `error` | str or None | Step 3 if no results | Displayed in interface |

---

## Error Handling

### search_listings — no results
**Failure mode:** No listings match the query after filtering 
by description keywords, size, and price.

**Agent response:** `session["error"]` is set to a message 
that includes the query terms and suggests trying a broader 
description, different size, or higher budget. The session 
is returned immediately. `suggest_outfit` and `create_fit_card` 
are never called.

**Concrete example from testing:**

Query: "designer ballgown size XXS under $5"
→ search_listings returns []
→ session["error"] = "No listings found matching 'designer ballgown'
in size XXS under $5.00. Try a broader description, a different
size, or a higher budget."
→ session["fit_card"] = None
→ session["outfit_suggestion"] = None

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.


---

### suggest_outfit — empty wardrobe
**Failure mode:** `wardrobe["items"]` is an empty list — 
the user has not provided any wardrobe items.

**Tool response:** Detects the empty wardrobe and sends a 
general styling prompt to the LLM instead of a wardrobe-specific 
prompt. Returns a string with general advice about what kinds 
of pieces pair well with the item. Never raises an exception 
or returns an empty string.

**Concrete example from testing:**
```python
suggest_outfit(item, get_empty_wardrobe())
→ "This faded graphic tee has a relaxed, streetwear-ready feel. 
   Pair it with wide-leg or baggy jeans for a classic 90s look, 
   or tuck it into high-waisted trousers for a more polished take. 
   Chunky sneakers or clean white shoes keep it fresh."
```

---

### create_fit_card — empty outfit string
**Failure mode:** `outfit` argument is empty or whitespace-only.

**Tool response:** Returns the error string 
`"Unable to generate a fit card — no outfit suggestion was provided."` 
without calling the LLM. Does not raise an exception.

**Concrete example from testing:**
```python
create_fit_card("", item)
→ "Unable to generate a fit card — no outfit suggestion was provided."

create_fit_card("   ", item)
→ "Unable to generate a fit card — no outfit suggestion was provided."
```

---

### expected_budget — budget out of range
**Failure mode:** Budget is too low for any single item, 
or too large such that all items fit but the total is not 
within the ±$10 window.

**Tool response:** Returns an informative string message 
describing the situation and suggesting what to try instead. 
Does not raise an exception.

**Concrete example from testing:**
```python
expected_budget(3.0)
→ "No items are available within your budget range ($-7.00–$13.00). 
   The cheapest item is $12.00. Try a higher budget."
```

---

## Spec Reflection

**One way the spec helped:**
Writing the architecture diagram in `planning.md` before any 
code was the most valuable part of the planning process. The 
diagram showed exactly what data needed to flow between each 
step — `selected_item` from Step 4 into both `suggest_outfit` 
and `create_fit_card`, `outfit_suggestion` from Step 5 into 
Step 6 — which made implementing the session dict in `agent.py` 
straightforward. Without the diagram, it would have been easy 
to lose track of which tool needed which input and implement 
the state management incorrectly.

**One way implementation diverged from the spec:**
The spec described `search_listings` returning only relevant 
results by dropping items with a score of zero. In practice, 
items with a score of 1 or 2 (matching only the word "vintage" 
in their tags) were appearing at the end of results for queries 
like "vintage graphic tee" — items like leather belts and 
Chelsea boots that shared a single tag but were completely 
unrelated to the search intent. The minimum score threshold 
was raised from `> 0` to `>= 3` after testing, which requires 
at least one title match or a combination of tag and description 
matches before a listing is returned. This was not specified in 
`planning.md` and emerged only from seeing real output.

---

## AI Usage

**Instance 1 — tools.py implementation:**
I provided Claude with the full `planning.md` spec and the 
docstrings already present in `tools.py` (which described the 
function signatures, input parameters, return values, and 
failure modes for each tool). I asked Claude to implement 
all four functions matching the spec exactly. Claude produced 
working implementations for all four tools. I reviewed the 
`search_listings` scoring logic and directed Claude to weight 
title matches at 3 points, style tag matches at 2 points, and 
description matches at 1 point — the initial version treated 
all matches equally. I also directed it to implement size 
priority ordering (exact match first, then contains match, 
then One Size) which was specified in planning.md but not 
fully captured in the initial output.

**Instance 2 — test_tools.py implementation:**
I provided Claude with the base test cases already written 
and asked it to add tests covering every failure mode 
described in `planning.md` — empty results, empty wardrobe, 
empty outfit string, budget out of range — plus structural 
tests confirming return types and field presence. Claude 
produced a comprehensive test file covering all four tools. 
I reviewed each test and added `test_create_fit_card_varies_output` 
myself after noticing that none of the generated tests verified 
that `create_fit_card` produces different output on repeated 
calls, which is a requirement stated in the project spec 
(the tool should not return identical captions for the same 
input).

---

## Running Tests

```bash
pytest tests/test_tools.py -v
```

All 22 tests should pass. Tests cover: search result validity, 
price filtering, size priority ordering, empty result handling, 
outfit generation with and without a wardrobe, fit card 
generation and failure modes, and budget combination validity.