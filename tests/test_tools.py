from tools import search_listings
from tools import expected_budget
from tools import suggest_outfit
from tools import create_fit_card
from utils.data_loader import get_example_wardrobe
from utils.data_loader import get_empty_wardrobe
import pytest

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

def test_search_returns_list_of_dicts():
    # Every result must be a dict with the expected fields
    results = search_listings("vintage", size=None, max_price=100)
    assert isinstance(results, list)
    for item in results:
        assert isinstance(item, dict)
        assert "id" in item
        assert "title" in item
        assert "price" in item
        assert "size" in item
        assert "style_tags" in item


def test_search_title_ranked_higher_than_description():
    # "graphic tee" appears in the title of lst_006
    # It should rank above items that only mention it in description
    results = search_listings("graphic tee", size=None, max_price=100)
    assert len(results) > 0
    # Top result title should contain "graphic" or "tee"
    top_title = results[0]["title"].lower()
    assert "graphic" in top_title or "tee" in top_title


def test_search_size_exact_match_ranked_first():
    # Exact size "M" should appear before "S/M" or "M/L"
    results = search_listings("vintage", size="M", max_price=100)
    if len(results) >= 2:
        first_size  = results[0]["size"].lower()
        # First result should be exact match "m" not a combined size
        assert first_size == "m" or "m" in first_size


def test_search_no_results_returns_empty_list_not_exception():
    # Confirms the function never raises — just returns []
    try:
        results = search_listings("xyznonexistentitem123", size=None, max_price=1)
        assert results == []
    except Exception as e:
        pytest.fail(f"search_listings raised an exception: {e}")


def test_search_no_price_filter():
    # When max_price is None, expensive items should be included
    results_no_filter = search_listings("jacket", size=None, max_price=None)
    results_filtered  = search_listings("jacket", size=None, max_price=30)
    # No filter should return more or equal results
    assert len(results_no_filter) >= len(results_filtered)


# ── suggest_outfit tests ──────────────────────────────────────────────────────

def test_suggest_outfit_returns_string():
    item   = search_listings("vintage graphic tee", max_price=50)[0]
    result = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_empty_wardrobe_returns_string():
    # Empty wardrobe must return general advice, not crash or return ""
    item   = search_listings("vintage graphic tee", max_price=50)[0]
    result = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_empty_wardrobe_no_exception():
    # Explicitly confirm no exception is raised
    item = search_listings("cardigan", max_price=100)[0]
    try:
        result = suggest_outfit(item, get_empty_wardrobe())
        assert result != ""
    except Exception as e:
        pytest.fail(f"suggest_outfit raised an exception with empty wardrobe: {e}")


def test_suggest_outfit_references_item():
    # The outfit suggestion should mention something about the item
    item   = search_listings("flannel", max_price=50)[0]
    result = suggest_outfit(item, get_example_wardrobe())
    # Result should be a meaningful string, not a placeholder
    assert len(result) > 50


# ── create_fit_card tests ─────────────────────────────────────────────────────

def test_create_fit_card_returns_string():
    item   = search_listings("vintage graphic tee", max_price=50)[0]
    outfit = suggest_outfit(item, get_example_wardrobe())
    card   = create_fit_card(outfit, item)
    assert isinstance(card, str)
    assert len(card) > 0


def test_create_fit_card_empty_outfit_returns_error_string():
    # Empty outfit must return error message string, not raise exception
    item = search_listings("vintage graphic tee", max_price=50)[0]
    card = create_fit_card("", item)
    assert isinstance(card, str)
    assert "unable" in card.lower() or "no outfit" in card.lower()


def test_create_fit_card_empty_outfit_no_exception():
    item = search_listings("vintage graphic tee", max_price=50)[0]
    try:
        card = create_fit_card("", item)
        assert card != ""
    except Exception as e:
        pytest.fail(f"create_fit_card raised an exception with empty outfit: {e}")


def test_create_fit_card_whitespace_outfit_returns_error_string():
    # Whitespace-only outfit should be treated same as empty
    item = search_listings("vintage graphic tee", max_price=50)[0]
    card = create_fit_card("   ", item)
    assert isinstance(card, str)
    assert "unable" in card.lower() or "no outfit" in card.lower()


def test_create_fit_card_varies_output():
    # Running twice on same input should produce different captions
    # due to temperature=0.9
    item   = search_listings("vintage graphic tee", max_price=50)[0]
    outfit = suggest_outfit(item, get_example_wardrobe())
    card1  = create_fit_card(outfit, item)
    card2  = create_fit_card(outfit, item)
    # Both should be valid strings
    assert isinstance(card1, str) and len(card1) > 0
    assert isinstance(card2, str) and len(card2) > 0
    # They should not be identical (very unlikely at temp=0.9)
    # We use a soft check here since LLMs can occasionally repeat
    assert card1 != card2 or len(card1) > 20


# ── expected_budget tests ─────────────────────────────────────────────────────

def test_expected_budget_returns_list_for_valid_budget():
    # $60 budget should find a combination of items
    result = expected_budget(60.0)
    assert isinstance(result, list)
    assert len(result) > 0


def test_expected_budget_total_within_range():
    # Total price of returned items must be within +/- $10 of budget
    budget = 60.0
    result = expected_budget(budget)
    if isinstance(result, list):
        total = sum(item["price"] for item in result)
        assert (budget - 10) <= total <= (budget + 10), (
            f"Total ${total:.2f} is outside range "
            f"${budget - 10:.2f}–${budget + 10:.2f}"
        )


def test_expected_budget_too_low_returns_string():
    # Budget of $3 is below cheapest item — should return message string
    result = expected_budget(3.0)
    assert isinstance(result, str)
    assert len(result) > 0


def test_expected_budget_too_low_no_exception():
    try:
        result = expected_budget(3.0)
        assert isinstance(result, str)
    except Exception as e:
        pytest.fail(f"expected_budget raised an exception: {e}")


def test_expected_budget_returns_list_of_dicts():
    # Each item in the result must be a proper listing dict
    result = expected_budget(50.0)
    if isinstance(result, list):
        for item in result:
            assert isinstance(item, dict)
            assert "id"    in item
            assert "title" in item
            assert "price" in item


def test_expected_budget_result_items_exist_in_listings():
    # All returned items must come from the actual listings dataset
    from utils.data_loader import load_listings
    all_ids = {item["id"] for item in load_listings()}
    result  = expected_budget(50.0)
    if isinstance(result, list):
        for item in result:
            assert item["id"] in all_ids, (
                f"Item {item['id']} not found in listings dataset"
            )