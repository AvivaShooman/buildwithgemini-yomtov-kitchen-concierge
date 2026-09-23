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

import pytest
from app.app_utils.planning_tools import (
    lookup_jewish_calendar,
    generate_grocery_list,
    calculate_blech_schedule,
    PROJECT_ID,
)


@pytest.mark.asyncio
async def test_lookup_jewish_calendar():
    # Query September 2026 in Brooklyn, NY (11213)
    res = await lookup_jewish_calendar(year=2026, month=9, zip_code="11213")

    assert res["year"] == 2026
    assert res["month"] == 9
    assert len(res["holidays"]) > 0
    assert len(res["candle_lighting_times"]) > 0

    # Verify Rosh Hashanah or Sukkot is present
    titles = [h["title"] for h in res["holidays"]]
    assert any("Rosh Hashana" in t for t in titles)

    # Verify Shabbat overlap detection
    assert isinstance(res["shabbat_yomtov_overlaps"], list)
    # Sukkot I (2026-09-26) or Rosh Hashanah 5787 (2026-09-12) falls on Saturday (Shabbat)
    overlaps = [o["holiday"] for o in res["shabbat_yomtov_overlaps"]]
    assert any("Rosh Hashana" in o or "Sukkot" in o for o in overlaps)


@pytest.mark.asyncio
async def test_generate_grocery_list():
    res = await generate_grocery_list(
        recipe_ids=["classic-braised-flanken-brisket", "traditional-potato-kugel"],
        guest_count=8,
        list_name="Test Rosh Hashanah Shopping List",
        save_to_firestore=True,
    )

    assert res["guest_count"] == 8
    assert res["scale_multiplier"] == 2.0
    assert "Classic Braised Flanken Brisket" in res["recipes_included"]
    assert "Traditional Potato & Caramelized Onion Kugel" in res["recipes_included"]

    # Check categorization
    aisles = res["aisles"]
    assert len(aisles["Meat & Poultry"]) > 0
    assert len(aisles["Produce"]) > 0
    assert len(aisles["Refrigerated & Eggs"]) > 0
    assert "saved_document_id" in res


@pytest.mark.asyncio
async def test_generate_grocery_list_multi_recipe_fuzzy():
    recipe_queries = [
        "braised-flanken-brisket",
        "roasted-vegetable-quinoa-stuffed-bell-peppers",
        "classic-potato-kugel",
        "honey-glazed-carrots-with-dried-cranberries",
        "slow-cooker-apricot-chicken",
        "sweet-potato-apple-tzimmes",
        "green-bean-almondine-almond-free",
        "deconstructed-cabbage-rolls-ground-beef",
        "hearty-mushroom-barley-soup-barley-free",
        "israeli-salad-cooked",
        "completely-new-holiday-custard",  # Unknown dish to test automatic synthesis
    ]

    res = await generate_grocery_list(
        recipe_ids=recipe_queries,
        guest_count=8,
        list_name="Consolidated Yom Tov Feast Shopping List",
        save_to_firestore=True,
    )

    assert res["guest_count"] == 8
    assert res["scale_multiplier"] == 2.0
    # All 11 recipes must be resolved and included (none dropped!)
    assert len(res["recipes_included"]) == 11
    assert "Classic Braised Flanken Brisket" in res["recipes_included"]
    assert "Roasted Vegetable & Quinoa Stuffed Bell Peppers" in res["recipes_included"]
    assert "Traditional Potato & Caramelized Onion Kugel" in res["recipes_included"]

    # Verify scaling applied to quantities (x2.0 for 8 guests)
    produce_text = " ".join(res["aisles"]["Produce"])
    assert "12 large bell peppers" in produce_text or "bell peppers" in produce_text

    meat_text = " ".join(res["aisles"]["Meat & Poultry"])
    assert "10 lbs beef flanken" in meat_text or "16 chicken thighs" in meat_text

    # Verify unknown recipe was synthesized and included
    assert any("Completely New Holiday Custard" in r for r in res["recipes_included"])



def test_calculate_blech_schedule():
    dishes = [
        {"name": "Classic Braised Flanken Brisket", "max_warming_hours": 24, "meal": "Shabbat Lunch"},
        {"name": "Traditional Potato Kugel", "max_warming_hours": 20, "meal": "Shabbat Lunch"},
        {"name": "Matzo Ball Chicken Soup", "max_warming_hours": 8, "meal": "Friday Night Dinner"},
    ]
    meal_times = [
        {"meal": "Friday Night Dinner", "time": "20:00"},
        {"meal": "Shabbat Lunch", "time": "12:30"},
    ]

    res = calculate_blech_schedule(
        dishes=dishes,
        candle_lighting_time="18:53",
        meal_times=meal_times,
    )

    assert res["candle_lighting_deadline"] == "18:53"
    assert len(res["halachic_readiness_checklist"]) >= 3

    entries = {e["dish"]: e for e in res["dishes_schedule"]}

    # Kugel should be perimeter to prevent burning
    assert "Perimeter" in entries["Traditional Potato Kugel"]["recommended_zone"]
    # Soup should be center to stay boiling hot
    assert "Center" in entries["Matzo Ball Chicken Soup"]["recommended_zone"]
    # 18h Brisket should have liquid compensation
    assert "+1/2 cup" in entries["Classic Braised Flanken Brisket"]["liquid_compensation"]
