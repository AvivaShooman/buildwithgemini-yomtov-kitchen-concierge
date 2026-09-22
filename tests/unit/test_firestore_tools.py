# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for Firestore recipe and rating backend tools."""

import pytest
from app.app_utils.firestore_tools import (
    PROJECT_ID,
    _validate_rating,
    _slugify,
    search_firestore_recipes,
    get_firestore_recipe,
    save_firestore_recipe,
    update_firestore_recipe_rating,
)


def test_hardcoded_project_id():
    """Verify that the project ID is hardcoded and non-empty to satisfy deployment constraints."""
    assert PROJECT_ID == "qwiklabs-gcp-04-ded35b1abcfb"
    assert not PROJECT_ID.isdigit(), "Project ID must not be a numeric ID"


def test_slugify():
    assert _slugify("Classic Braised Flanken Brisket!") == "classic-braised-flanken-brisket"
    assert _slugify("Sweet & Savory Roast Chicken") == "sweet-savory-roast-chicken"


def test_validate_rating():
    assert _validate_rating("crowd", 1) == 1
    assert _validate_rating("crowd", 5) == 5
    with pytest.raises(ValueError, match="between 1 and 5"):
        _validate_rating("crowd", 0)
    with pytest.raises(ValueError, match="between 1 and 5"):
        _validate_rating("crowd", 6)
    with pytest.raises(ValueError, match="integer"):
        _validate_rating("crowd", "invalid")


@pytest.mark.asyncio
async def test_search_firestore_recipes_by_holiday_and_blech():
    results = await search_firestore_recipes(holiday="Pesach", blech_friendly=True)
    assert len(results) >= 2
    titles = [r["title"] for r in results]
    assert "Classic Braised Flanken Brisket" in titles
    assert "Traditional Potato & Caramelized Onion Kugel" in titles


@pytest.mark.asyncio
async def test_search_firestore_recipes_allergen_exclusion():
    # Exclude eggs: Traditional Potato Kugel contains eggs and must be filtered out
    results_no_eggs = await search_firestore_recipes(exclude_allergens=["eggs"])
    titles = [r["title"] for r in results_no_eggs]
    assert "Traditional Potato & Caramelized Onion Kugel" not in titles

    # Exclude fish: Lemon Herb Poached Salmon must be filtered out
    results_no_fish = await search_firestore_recipes(exclude_allergens=["fish"])
    titles_no_fish = [r["title"] for r in results_no_fish]
    assert "Lemon Herb Poached Salmon with Fresh Dill" not in titles_no_fish


@pytest.mark.asyncio
async def test_get_firestore_recipe():
    recipe = await get_firestore_recipe("classic-braised-flanken-brisket")
    assert recipe["id"] == "classic-braised-flanken-brisket"
    assert recipe["title"] == "Classic Braised Flanken Brisket"
    assert recipe["blech_friendly"] is True
    assert "ratings" in recipe
    assert recipe["ratings"]["yomtov_suitability"] == 5.0

    not_found = await get_firestore_recipe("nonexistent-dish-xyz")
    assert "error" in not_found


@pytest.mark.asyncio
async def test_save_and_update_recipe_rating():
    # Save a test recipe
    save_res = await save_firestore_recipe(
        title="Test Sweet Tzimmes with Prunes",
        holidays=["Rosh Hashanah", "Sukkot"],
        course="side",
        kashrut="pareve",
        ingredients=["4 sweet potatoes", "1 cup pitted prunes", "1/4 cup honey", "1 tsp cinnamon"],
        instructions="Simmer covered until glazed and tender.",
        allergens=[],
        dietary_tags=["gluten-free", "nut-free", "sesame-free", "vegan"],
        blech_friendly=True,
        warming_drawer_friendly=True,
        max_warming_hours=18,
        evaporation_compensation="Add 2 tbsp water or orange juice if warming over 12h",
        day2_leftover_quality="Great",
        crowd_rating=4.5,
        ease_of_prep=5.0,
        yomtov_suitability=4.8,
        notes="Traditional sweet Rosh Hashanah side.",
    )
    assert save_res["status"] == "success"
    recipe_id = save_res["recipe_id"]
    assert recipe_id == "test-sweet-tzimmes-with-prunes"

    # Verify retrieval
    retrieved = await get_firestore_recipe(recipe_id)
    assert retrieved["title"] == "Test Sweet Tzimmes with Prunes"

    # Update rating
    update_res = await update_firestore_recipe_rating(
        recipe_id=recipe_id,
        crowd_rating=5,
        ease_of_prep=5,
        yomtov_suitability=5,
        notes="Held up superbly on the blech, sweetness deepened.",
    )
    assert update_res["status"] == "success"
    assert update_res["updated_ratings"]["review_count"] == 2
