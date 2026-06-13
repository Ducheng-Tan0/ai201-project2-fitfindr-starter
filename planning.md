# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
- `size` (str): Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
- `max_price` (float):  Maximum price (inclusive), or None to skip price filtering.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
A list of matching listing dicts, sorted by relevance (best match first).
        
**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
Returns an empty list if nothing matches — does NOT raise an exception.
---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): A listing dict (the item the user is considering buying).
- `wardrobe` (dict):  A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

**What it returns:**
 A non-empty string with outfit suggestions.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If the wardrobe is empty, offer general styling advice for the item rather than raising an exception or returning an empty string.
---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Generate a short, shareable outfit caption for the thrifted find.
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion string from suggest_outfit().
- `new_item` (dict): The listing dict for the thrifted item
**What it returns:**
<!-- Describe the return value -->
A 2–4 sentence string usable as an Instagram/TikTok caption.
        
**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If outfit is empty or missing, return a descriptive error message string — do NOT raise an exception.
---

### Additional Tools : expected_budget

<!-- Copy the block above for any tools beyond the required three -->
**What it does:**
The user can state their estimate budget, and it will generate/filter out a combination of finds priced at around that budget. 
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `budget` (float): The estimated budget from the user 

**What it returns:**
<!-- Describe the return value -->
Returns a a combination of items from the listings that is +/-10 (currency) of the budget (float). 
        
**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
This may mean that every find is priced above the budget or budget is too large such that all finds can be purchased. Suggest user for a new budget input or state no availablity currently for such budget. 

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The planning loop follows a conditional sequence based on what each 
tool returns. It does not call all tools unconditionally — it checks 
results at each step before proceeding.

The logic is as follows:

Step 1 — Parse the query:
The agent receives a natural language query string. It uses the Groq 
LLM to extract three fields from the query:
- description (str): what item the user is looking for
- size (str or None): size mentioned, or None if not specified
- max_price (float or None): price ceiling mentioned, or None if not specified

The parsed values are stored in session["parsed"].

Step 2 — Call search_listings():
Call search_listings(description, size, max_price) using the parsed values.
Store the result in session["search_results"].

Check: if session["search_results"] is an empty list:
  → Set session["error"] to: "No listings found matching your search. 
    Try a broader description, a different size, or a higher budget."
  → Return the session immediately.
  → Do NOT proceed to suggest_outfit.

If results are not empty:
  → Set session["selected_item"] = session["search_results"][0]
    (the highest-scoring match)
  → Proceed to Step 3.

Step 3 — Call suggest_outfit():
Call suggest_outfit(session["selected_item"], session["wardrobe"]).
Store the result in session["outfit_suggestion"].

The tool handles an empty wardrobe internally — it returns general 
styling advice rather than crashing. No branching needed here at the 
planning loop level.

Step 4 — Call create_fit_card():
Call create_fit_card(session["outfit_suggestion"], session["selected_item"]).
Store the result in session["fit_card"].

The tool handles an empty outfit string internally. No branching needed 
at the planning loop level.

Step 5 — Return the session:
Return the completed session dict with fit_card, outfit_suggestion, 
selected_item, and search_results all populated. session["error"] 
remains None on a successful run.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
All state is stored in a single session dict initialized by _new_session() 
at the start of each interaction. The session dict has these fields:

- session["query"]: the original user query string, never modified
- session["parsed"]: dict with keys "description", "size", "max_price" 
  extracted from the query by the LLM parser
- session["search_results"]: list of listing dicts returned by 
  search_listings(). Each dict has fields: id, title, description, 
  category, style_tags, size, condition, price, colors, brand, platform
- session["selected_item"]: single listing dict — always results[0], 
  the top-scored match. This is passed directly into suggest_outfit() 
  and create_fit_card() without any transformation
- session["wardrobe"]: the wardrobe dict passed in at the start. Has 
  an "items" key containing a list of wardrobe item dicts, each with: 
  id, name, category, colors, style_tags, notes. Never modified during 
  the session.
- session["outfit_suggestion"]: string returned by suggest_outfit(). 
  Passed directly into create_fit_card() as the outfit argument.
- session["fit_card"]: string returned by create_fit_card(). 
  This is the final output shown to the user.
- session["error"]: None on success. Set to a human-readable string 
  if the interaction ends early (currently only when search_listings 
  returns an empty list).

No tool modifies the session dict directly — only run_agent() reads 
from and writes to the session. Tools receive their inputs as arguments 
and return values, which run_agent() then stores in the session.
---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No listings match the query (empty list returned) | Agent sets session["error"] to: "No listings found matching your search. Try a broader description, a different size, or a higher budget." Returns session immediately without calling suggest_outfit or create_fit_card. |
| suggest_outfit | wardrobe["items"] is an empty list | Tool detects the empty wardrobe and calls the LLM with a general styling prompt: "Given only this item, what would be good ways to style it?" Returns styling advice as a string. Never raises an exception or returns an empty string. |
| create_fit_card | outfit argument is empty or whitespace-only | Tool returns the string: "Unable to generate a fit card — no outfit suggestion was provided." Does not call the LLM and does not raise an exception. |


---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->
User query + wardrobe

│

▼

┌─────────────────────────────────────────┐

│           run_agent()                   │

│         Planning Loop                   │

│                                         │

│  Step 1: Parse query via Groq LLM       │

│    └─► session["parsed"]                │

│         {description, size, max_price}  │

│                                         │

│  Step 2: search_listings()              │◄── session["parsed"]

│    │                                    │

│    ├── results == [] ───────────────────┼──► session["error"] set

│    │                                    │    return session early

│    │                                    │

│    └── results != [] ──────────────────►│

│         session["search_results"]       │

│         session["selected_item"]        │

│              = results[0]               │

│                                         │

│  Step 3: suggest_outfit()               │◄── session["selected_item"]

│    │    (new_item, wardrobe)            │◄── session["wardrobe"]

│    │                                    │

│    ├── wardrobe empty ─────────────────►│ tool returns general

│    │                                    │ styling advice (no crash)

│    │                                    │

│    └── wardrobe not empty ─────────────►│

│         session["outfit_suggestion"]    │

│                                         │

│  Step 4: create_fit_card()              │◄── session["outfit_suggestion"]

│    │    (outfit, new_item)              │◄── session["selected_item"]

│    │                                    │

│    ├── outfit empty ───────────────────►│ tool returns error string

│    │                                    │ (no crash)

│    │                                    │

│    └── outfit not empty ───────────────►│

│         session["fit_card"]             │

│                                         │

│  Step 5: return session                 │

└─────────────────────────────────────────┘

│

▼

session dict returned:

{
selected_item:  listing dict,
outfit_suggestion:  str,
fit_card:   str,
error:   None (or error message)
}
---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
I will use Claude for all three tools, one at a time.

search_listings:
- Input to Claude: the Tool 1 spec block from planning.md (inputs, 
  return value, failure mode) plus the listing dict field list from 
  data_loader.py (id, title, description, category, style_tags, size, 
  condition, price, colors, brand, platform)
- Ask Claude to implement search_listings() using load_listings() 
  from utils/data_loader.py, filtering by max_price and size, scoring 
  by keyword overlap between description and the title + description + 
  style_tags fields, and returning an empty list (not an exception) 
  when nothing matches
- Verify by running 3 test queries: one with results, one with no 
  results, one with a price filter — confirm empty list returned not 
  an exception, confirm all returned items have price <= max_price

suggest_outfit:
- Input to Claude: the Tool 2 spec block, the listing dict structure, 
  and the wardrobe schema showing wardrobe["items"] with fields: 
  id, name, category, colors, style_tags, notes
- Ask Claude to implement suggest_outfit() calling Groq with 
  llama-3.3-70b-versatile, handling the empty wardrobe case by 
  returning general styling advice instead of crashing
- Verify by running once with get_example_wardrobe() (should return 
  specific outfit combinations) and once with get_empty_wardrobe() 
  (should return general styling advice, not an empty string)

create_fit_card:
- Input to Claude: the Tool 3 spec block, the listing dict structure, 
  and the caption style guidelines (casual, mentions item name + price 
  + platform, captures outfit vibe)
- Ask Claude to implement create_fit_card() with a guard against empty 
  outfit string, calling Groq with temperature=0.9 to ensure varied outputs
- Verify by running it twice on the same input and confirming the 
  captions are different, and by running it with an empty outfit string 
  and confirming it returns an error message string not an exception
**Milestone 4 — Planning loop and state management:**
I will use Claude for the planning loop implementation.

- Input to Claude: the Planning Loop section, State Management section, 
  and Architecture diagram from this planning.md, plus the session dict 
  structure from agent.py (_new_session() function)
- Ask Claude to implement run_agent() following the 7 steps in the 
  TODO, using the Groq LLM to parse the query in Step 2, branching on 
  empty search results in Step 3, and storing all intermediate values 
  in the session dict
- Verify by running the two test cases already in agent.py:
  1. Happy path: "vintage graphic tee under $30" with get_example_wardrobe() 
     — confirm session["fit_card"] is not None and session["error"] is None
  2. No-results path: "designer ballgown size XXS under $5" 
     — confirm session["error"] is set and session["fit_card"] is None
---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
This step parse the query. First run_agent() calls the Groq LLM with the query string and asks it to 
extract structured fields. The LLM returns:
- description: "vintage graphic tee"
- size: None (no size mentioned)
- max_price: 30.0
**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
search_listings("vintage graphic tee", size=None, max_price=30.0) 
is called. load_listings() returns all 40 listings. The function:
- Filters out listings with price > 30.0 
  (removes lst_001 $38, lst_004 $45, lst_007 $42, lst_009 $55, 
  lst_019 $48, lst_022 $75, lst_036 $52 and others above $30)
- Scores remaining listings by keyword overlap with "vintage graphic tee" 
  against each listing's title, description, and style_tags
- Top matches: lst_006 "Graphic Tee — 2003 Tour Bootleg Style" ($24) 
  scores highest due to "graphic tee" in title and style_tags, 
  lst_033 "Vintage Band Tee — Faded Grey" ($19) scores second

session["search_results"] = [lst_006, lst_033, ...]
session["selected_item"] = lst_006 (top result)

Results are not empty so the agent does not return early.
**Step 3:**
<!-- Continue until the full interaction is complete -->
suggest_outfit(session["selected_item"], session["wardrobe"]) is called.

session["selected_item"] is lst_006:
- title: "Graphic Tee — 2003 Tour Bootleg Style"
- style_tags: ["graphic tee", "vintage", "grunge", "streetwear", "band tee"]
- colors: ["black"]
- price: $24.00
- platform: depop

session["wardrobe"] is get_example_wardrobe() which contains:
- Baggy straight-leg jeans dark wash (w_001)
- White ribbed tank top (w_003)
- Black combat boots (w_008)
- Chunky white sneakers (w_007)
- Vintage black denim jacket (w_006)

The LLM receives both and returns:
"Outfit 1: Pair the boxy graphic tee with your baggy dark wash jeans 
and chunky white sneakers for a classic 90s streetwear look. Add your 
vintage black denim jacket on top for layering.
Outfit 2: Tuck the front of the tee into your wide-leg khaki trousers 
and finish with black combat boots for a grunge-meets-minimal vibe."

**Step 4: Call create_fit_card()**
create_fit_card(session["outfit_suggestion"], session["selected_item"]) 
is called. The LLM receives the outfit suggestion and item details and 
returns a caption:

"found this 2003 bootleg tee on depop for $24 and it was made for my 
baggy jeans styled it with chunky sneakers and a denim jacket and 
honestly the fit came together instantly. thrift szn never misses"

session["fit_card"] = the string above.

**Step 5: Return the session**
run_agent() returns the completed session dict:
- session["selected_item"]: lst_006 listing dict
- session["outfit_suggestion"]: two outfit combinations
- session["fit_card"]: Instagram-ready caption
- session["error"]: None

**Final output to user:**
The Gradio interface displays three panels:
1. Found item: "Graphic Tee — 2003 Tour Bootleg Style — $24 on depop"
2. Outfit suggestion: the two outfit combinations from suggest_outfit
3. Fit card: the shareable caption from create_fit_card
<!-- What does the user actually see at the end? -->
