"""
app.py

Gradio interface for FitFindr. The layout and wiring are already set up —
your job is to fill in handle_query() so it calls run_agent() and maps
the session results to the three output panels.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860,
but check your terminal — the port may differ).
"""

import gradio as gr
from agent import run_agent
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

    # ── Top result — full details ─────────────────────────────────────────────
    colors   = ", ".join(item.get("colors", []))
    tags     = ", ".join(item.get("style_tags", []))
    brand    = item.get("brand") or "Unknown brand"

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

    # ── All other results ─────────────────────────────────────────────────────
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
    """Returns the outfit suggestion or an appropriate message."""
    if session.get("error"):
        return "No outfit generated — search returned no results."

    outfit = session.get("outfit_suggestion")
    if not outfit:
        return "No outfit suggestion available."

    return outfit


def _format_fit_card(session: dict) -> str:
    """Returns the fit card or an appropriate message."""
    if session.get("error"):
        return "No fit card generated — search returned no results."

    fit_card = session.get("fit_card")
    if not fit_card:
        return "No fit card available."

    return fit_card


# ── handle_query ──────────────────────────────────────────────────────────────

def handle_query(question: str, use_example_wardrobe: bool) -> tuple[str, str, str]:
    """
    Called every time the user clicks Find or presses Enter.

    Step 1: Validate the input — return early if empty
    Step 2: Choose wardrobe based on toggle
    Step 3: Call run_agent() with the query and wardrobe
    Step 4: Map session dict to three output strings
    Step 5: Return the three strings to Gradio
    """

    # Step 1: Validate
    if not question or not question.strip():
        return (
            "Please enter a search query.",
            "",
            ""
        )

    # Step 2: Choose wardrobe
    wardrobe = get_example_wardrobe() if use_example_wardrobe \
               else get_empty_wardrobe()

    # Step 3: Run the agent
    session = run_agent(question.strip(), wardrobe)

    # Step 4 + 5: Map session to output panels
    return (
        _format_selected_item(session),
        _format_outfit(session),
        _format_fit_card(session)
    )


# ── Gradio interface ──────────────────────────────────────────────────────────

with gr.Blocks(
    title="FitFindr",
    theme=gr.themes.Soft()
) as demo:

    gr.Markdown("""
    # 👗 FitFindr
    **Find secondhand pieces and build outfits around them.**
    Describe what you're looking for — include size and budget if you have them.
    """)

    # ── Input row ─────────────────────────────────────────────────────────────
    with gr.Row():
        query_box = gr.Textbox(
            label="What are you looking for?",
            placeholder=(
                "e.g. vintage graphic tee under $30 size M, "
                "or: cozy oversized cardigan"
            ),
            lines=2,
            scale=4
        )

    with gr.Row():
        wardrobe_toggle = gr.Checkbox(
            label="Use example wardrobe for outfit suggestions",
            value=True
        )
        find_btn = gr.Button("Find", variant="primary", scale=1)

    # ── Output panels ─────────────────────────────────────────────────────────
    with gr.Row():
        item_box = gr.Textbox(
            label="Found Items",
            lines=16,
            scale=2
        )
        outfit_box = gr.Textbox(
            label="Outfit Suggestion",
            lines=16,
            scale=2
        )
        fitcard_box = gr.Textbox(
            label="Fit Card Caption",
            lines=16,
            scale=1
        )

    # ── Example queries ───────────────────────────────────────────────────────
    gr.Examples(
        examples=[
            ["vintage graphic tee under $30",               True],
            ["cozy oversized cardigan under $40",           True],
            ["baggy jeans size M under $45",                True],
            ["90s windbreaker",                             True],
            ["designer ballgown size XXS under $5",         False],
        ],
        inputs=[query_box, wardrobe_toggle],
        label="Try these examples"
    )

    # ── Wire up button and Enter key ──────────────────────────────────────────
    find_btn.click(
        fn=handle_query,
        inputs=[query_box, wardrobe_toggle],
        outputs=[item_box, outfit_box, fitcard_box]
    )

    query_box.submit(
        fn=handle_query,
        inputs=[query_box, wardrobe_toggle],
        outputs=[item_box, outfit_box, fitcard_box]
    )


# ── Launch ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting FitFindr...")
    print("Open your browser to: http://localhost:7860")
    demo.launch(inbrowser=True)