"""
app.py

Gradio interface for FitFindr. Calls run_agent() and maps the session
dict to the three output panels. Also exposes expected_budget as a
separate but integrated input.
"""

import gradio as gr
from agent import run_agent
from tools import expected_budget
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── Format helpers ────────────────────────────────────────────────────────────

def _format_selected_item(session: dict) -> str:
    """
    Formats the selected item and all search results for display.
    Shows full listing details for the top result, then lists
    all other results below it.
    """
    if session.get("error"):
        return f"No item found.\n\n{session['error']}"

    item = session.get("selected_item")
    if not item:
        return "No item selected."

    colors = ", ".join(item.get("colors", []))
    tags   = ", ".join(item.get("style_tags", []))
    brand  = item.get("brand") or "Unknown brand"

    top = (
        f"★ TOP RESULT\n"
        f"──────────────────────────────\n"
        f"Title     : {item['title']}\n"
        f"Price     : ${item['price']:.2f}\n"
        f"Platform  : {item['platform']}\n"
        f"Size      : {item['size']}\n"
        f"Condition : {item['condition']}\n"
        f"Category  : {item['category']}\n"
        f"Brand     : {brand}\n"
        f"Colors    : {colors}\n"
        f"Style tags: {tags}\n"
        f"──────────────────────────────\n"
        f"{item['description']}"
    )

    all_results = session.get("search_results", [])
    if len(all_results) <= 1:
        return top

    other_lines = ["\n\nALL RESULTS\n──────────────────────────────"]
    for i, r in enumerate(all_results):
        marker = "★" if i == 0 else f"{i + 1}."
        other_lines.append(
            f"{marker} {r['title']} — ${r['price']:.2f} "
            f"| {r['platform']} | size: {r['size']} "
            f"| condition: {r['condition']}"
        )

    return top + "\n".join(other_lines)


def _format_outfit(session: dict) -> str:
    if session.get("error"):
        return "No outfit generated — search returned no results."
    outfit = session.get("outfit_suggestion")
    if not outfit:
        return "No outfit suggestion available."
    return outfit


def _format_fit_card(session: dict) -> str:
    if session.get("error"):
        return "No fit card generated — search returned no results."
    fit_card = session.get("fit_card")
    if not fit_card:
        return "No fit card available."
    return fit_card


def _format_budget_results(results) -> str:
    """
    Formats the expected_budget results for display.
    Shows each item with full details and a total at the bottom.
    """
    if isinstance(results, str):
        # expected_budget returned an error message string
        return results

    if not results:
        return "No combination found for that budget."

    lines = ["BUDGET COMBINATION\n──────────────────────────────"]
    total = 0.0

    for i, item in enumerate(results, start=1):
        colors = ", ".join(item.get("colors", []))
        lines.append(
            f"\n{i}. {item['title']}\n"
            f"   Price     : ${item['price']:.2f}\n"
            f"   Platform  : {item['platform']}\n"
            f"   Size      : {item['size']}\n"
            f"   Condition : {item['condition']}\n"
            f"   Category  : {item['category']}\n"
            f"   Colors    : {colors}"
        )
        total += item["price"]

    lines.append(
        f"\n──────────────────────────────\n"
        f"TOTAL: ${total:.2f}"
    )

    return "\n".join(lines)


# ── Main query handler ────────────────────────────────────────────────────────

def handle_query(
    question: str,
    budget: float | None,
    use_example_wardrobe: bool
) -> tuple[str, str, str, str]:
    """
    Called every time the user clicks Find or presses Enter.

    Logic:
    - If question is filled AND budget is filled:
        Run main agent search (which uses max_price from parsed query
        OR budget as fallback), then also run expected_budget separately
    - If question is filled, budget is empty:
        Run main agent search only, no budget filtering
    - If question is empty, budget is filled:
        Run expected_budget only, skip main agent search
    - If both empty:
        Return validation message

    Returns four strings: item panel, outfit panel, fit card panel,
    budget panel.
    """

    question_filled = bool(question and question.strip())
    budget_filled   = budget is not None and budget > 0

    # ── Both empty ────────────────────────────────────────────────────────────
    if not question_filled and not budget_filled:
        return (
            "Please enter a search query or a budget amount.",
            "",
            "",
            ""
        )

    # ── Budget only — no search query ─────────────────────────────────────────
    if not question_filled and budget_filled:
        budget_output = _format_budget_results(expected_budget(budget))
        return (
            "No search query entered — showing budget combinations only.",
            "",
            "",
            budget_output
        )

    # ── Search query filled (with or without budget) ──────────────────────────
    wardrobe = get_example_wardrobe() if use_example_wardrobe \
               else get_empty_wardrobe()

    # If budget is provided but query doesn't mention a price,
    # append it so the parser picks it up
    query = question.strip()
    if budget_filled and "under" not in query.lower() \
                     and "$" not in query:
        query = f"{query} under ${budget:.0f}"

    # Run the main agent
    session = run_agent(query, wardrobe)

    item_output   = _format_selected_item(session)
    outfit_output = _format_outfit(session)
    card_output   = _format_fit_card(session)

    # Run expected_budget separately if budget provided
    if budget_filled:
        budget_output = _format_budget_results(expected_budget(budget))
    else:
        budget_output = "No budget entered — enter a budget amount to see item combinations."

    return item_output, outfit_output, card_output, budget_output


# ── Gradio interface ──────────────────────────────────────────────────────────

with gr.Blocks(
    title="FitFindr",
    theme=gr.themes.Soft()
) as demo:

    gr.Markdown("""
    # 👗 FitFindr
    **Find secondhand pieces and build outfits around them.**

    - Enter a search query to find items and get outfit suggestions
    - Enter a budget to find a combination of items near that total
    - Enter both to do all of the above at once
    """)

    # ── Input section ─────────────────────────────────────────────────────────
    with gr.Row():
        query_box = gr.Textbox(
            label="What are you looking for? (optional if using budget only)",
            placeholder=(
                "e.g. vintage graphic tee size M, "
                "or: cozy oversized cardigan under $40"
            ),
            lines=2,
            scale=3
        )
        budget_box = gr.Number(
            label="Total budget $ (optional)",
            placeholder="e.g. 60",
            minimum=0,
            scale=1
        )

    with gr.Row():
        wardrobe_toggle = gr.Checkbox(
            label="Use example wardrobe for outfit suggestions",
            value=True
        )
        find_btn = gr.Button("Find", variant="primary")

    # ── Output section ────────────────────────────────────────────────────────
    gr.Markdown("### Results")

    with gr.Row():
        item_box = gr.Textbox(
            label="Found Items",
            lines=18,
            scale=2
        )
        outfit_box = gr.Textbox(
            label="Outfit Suggestion",
            lines=18,
            scale=2
        )
        fitcard_box = gr.Textbox(
            label="Fit Card Caption",
            lines=18,
            scale=1
        )

    with gr.Row():
        budget_box_out = gr.Textbox(
            label="Budget Combinations",
            lines=18,
            scale=3
        )

    # ── Example queries ───────────────────────────────────────────────────────
    gr.Examples(
        examples=[
            ["vintage graphic tee under $30",    None,  True],
            ["cozy oversized cardigan",           40.0,  True],
            ["baggy jeans size M",                45.0,  True],
            ["",                                  60.0,  True],
            ["designer ballgown size XXS",        5.0,   False],
        ],
        inputs=[query_box, budget_box, wardrobe_toggle],
        label="Try these examples"
    )

    # ── Wire up ───────────────────────────────────────────────────────────────
    find_btn.click(
        fn=handle_query,
        inputs=[query_box, budget_box, wardrobe_toggle],
        outputs=[item_box, outfit_box, fitcard_box, budget_box_out]
    )

    query_box.submit(
        fn=handle_query,
        inputs=[query_box, budget_box, wardrobe_toggle],
        outputs=[item_box, outfit_box, fitcard_box, budget_box_out]
    )


# ── Launch ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting FitFindr...")
    print("Open your browser to: http://localhost:7860")
    demo.launch(inbrowser=True)