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
from app.app_utils.memory_tools import (
    _validate_rating,
    save_profile,
    save_past_meal_plan,
    record_dish_feedback,
    get_past_meal_history_and_feedback,
)


def test_validate_rating_bounds():
    assert _validate_rating("test", 1) == 1
    assert _validate_rating("test", 5) == 5
    assert _validate_rating("test", "3") == 3

    with pytest.raises(ValueError, match="between 1 and 5"):
        _validate_rating("test", 0)

    with pytest.raises(ValueError, match="between 1 and 5"):
        _validate_rating("test", 6)

    with pytest.raises(ValueError, match="must be an integer"):
        _validate_rating("test", "invalid")


@pytest.mark.asyncio
async def test_save_profile():
    # Household member
    res = await save_profile(
        name="Leah",
        is_guest=False,
        allergies=["tree nuts"],
        dietary_restrictions=["none"],
        likes=["fruit crumble"],
    )
    assert "HOUSEHOLD MEMBER" in res
    assert "Leah" in res
    assert "tree nuts" in res

    # Guest with multiple allergies
    res_guest = await save_profile(
        name="Uncle Dan",
        is_guest=True,
        allergies=["sesame", "peanuts"],
        dietary_restrictions=["gluten-free"],
        notes="Chassidish kashrut customs",
    )
    assert "GUEST" in res_guest
    assert "Uncle Dan" in res_guest
    assert "sesame, peanuts" in res_guest


@pytest.mark.asyncio
async def test_save_past_meal_plan():
    res = await save_past_meal_plan(
        holiday="Pesach",
        year=2025,
        meal_name="Night 1 Seder Dinner",
        dishes=["Brisket with Root Veg", "Matzo Ball Soup", "Potato Kugel"],
        guests=["Uncle Dan", "Cousin Avi"],
        notes="Brisket was very moist",
    )
    assert "Pesach 2025" in res
    assert "Night 1 Seder Dinner" in res
    assert "3 dishes recorded" in res


@pytest.mark.asyncio
async def test_record_dish_feedback():
    res = await record_dish_feedback(
        dish_name="Slow-Cooker Pomegranate Short Ribs",
        holiday_or_meal="Rosh Hashanah 2025 Dinner",
        crowd_rating=5,
        ease_of_prep=4,
        yomtov_suitability=5,
        notes="Held up perfectly in warming drawer for 18 hours.",
    )
    assert "Slow-Cooker Pomegranate Short Ribs" in res
    assert "Crowd: 5/5" in res
    assert "Prep: 4/5" in res
    assert "Yom Tov / Blech: 5/5" in res


@pytest.mark.asyncio
async def test_record_dish_feedback_invalid_rating():
    with pytest.raises(ValueError, match="between 1 and 5"):
        await record_dish_feedback(
            dish_name="Dry Chicken",
            holiday_or_meal="Yom Tov Lunch",
            crowd_rating=6,
            ease_of_prep=3,
            yomtov_suitability=1,
        )


@pytest.mark.asyncio
async def test_get_past_meal_history_no_context():
    res = await get_past_meal_history_and_feedback(query="brisket")
    assert "not available in this context" in res
