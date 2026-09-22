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

"""Planning and action tools: Jewish calendar lookup (Hebcal), grocery list generator, and blech scheduler."""

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from google.cloud import firestore

# Hardcoded project ID constraint
PROJECT_ID = "qwiklabs-gcp-04-ded35b1abcfb"

_firestore_client: firestore.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def _get_firestore_client() -> firestore.AsyncClient:
    global _firestore_client, _client_loop
    current_loop = asyncio.get_running_loop()
    if _firestore_client is None or _client_loop != current_loop:
        _firestore_client = firestore.AsyncClient(project=PROJECT_ID)
        _client_loop = current_loop
    return _firestore_client


async def lookup_jewish_calendar(
    year: int,
    month: int | None = None,
    zip_code: str | None = None,
) -> dict[str, Any]:
    """Look up Jewish holiday dates, candle lighting times, and Shabbat overlaps from Hebcal.

    Args:
        year: Gregorian year (e.g. 2026).
        month: Optional month number (1-12). If omitted, returns the whole year.
        zip_code: Optional 5-digit US ZIP code (e.g. '11213') to include local candle lighting and Havdalah times.

    Returns:
        A dictionary containing holidays, candle lighting times, and Shabbat-Yom Tov overlap notices.
    """
    params: dict[str, Any] = {
        "v": "1",
        "cfg": "json",
        "maj": "on",
        "min": "on",
        "nx": "on",
        "mf": "on",
        "ss": "on",
        "mod": "on",
        "s": "on",
        "year": str(year),
    }
    if month is not None:
        params["month"] = str(month)
    if zip_code:
        params["geo"] = "zip"
        params["zip"] = str(zip_code)
        params["c"] = "on"

    url = "https://www.hebcal.com/hebcal"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    holidays = []
    candle_lighting = []
    shabbat_overlaps = []

    for item in data.get("items", []):
        category = item.get("category", "")
        title = item.get("title", "")
        date_str = item.get("date", "")

        # Extract Day of Week (0 = Monday, ..., 5 = Saturday / Shabbat)
        try:
            item_date = datetime.fromisoformat(date_str[:10]).date()
            is_saturday = item_date.weekday() == 5
            day_name = item_date.strftime("%A")
        except Exception:
            is_saturday = False
            day_name = "Unknown"

        if category == "candles":
            candle_lighting.append({
                "title": title,
                "date": date_str,
                "memo": item.get("memo", ""),
            })
        elif category == "havdalah":
            candle_lighting.append({
                "title": title,
                "date": date_str,
                "memo": item.get("memo", ""),
            })
        elif category == "holiday":
            is_yomtov = item.get("yomtov", False)
            is_chol_hamoed = "CH''M" in title or "CH’’M" in title or "Chol HaMoed" in title or "חוה״מ" in item.get("hebrew", "")
            holiday_info = {
                "title": title,
                "hebrew": item.get("hebrew", ""),
                "date": date_str[:10],
                "day_of_week": day_name,
                "hebrew_date": item.get("hdate", ""),
                "is_yomtov": is_yomtov,
                "is_chol_hamoed": is_chol_hamoed,
                "is_shabbat": is_saturday,
                "memo": item.get("memo", ""),
            }
            holidays.append(holiday_info)

            # Check if Yom Tov or Major Holiday falls on Shabbat
            if is_yomtov and is_saturday:
                shabbat_overlaps.append({
                    "holiday": title,
                    "date": date_str[:10],
                    "notice": f"{title} falls on Shabbat. Halachic rule: Shabbat cooking restrictions strictly supersede Yom Tov allowances. Zero cooking or flame adjustment permitted.",
                })

    return {
        "year": year,
        "month": month,
        "location": data.get("location", {}).get("title", "Diaspora"),
        "total_holidays": len(holidays),
        "holidays": holidays,
        "candle_lighting_times": candle_lighting,
        "shabbat_yomtov_overlaps": shabbat_overlaps,
    }


async def generate_grocery_list(
    recipe_ids: list[str],
    guest_count: int = 4,
    list_name: str = "Holiday Grocery List",
    save_to_firestore: bool = True,
) -> dict[str, Any]:
    """Aggregate, scale, and categorize ingredients from Firestore recipes into a consolidated grocery list.

    Args:
        recipe_ids: List of Firestore recipe document IDs (e.g. ['classic-braised-flanken-brisket', 'traditional-potato-kugel']).
        guest_count: Total guest headcount to scale portions (recipes baseline is 4 servings).
        list_name: Name or label for the grocery list.
        save_to_firestore: Whether to persist the generated list into Firestore 'grocery_lists' collection.

    Returns:
        Structured grocery list categorized by supermarket aisle.
    """
    db = _get_firestore_client()
    scale = max(1, guest_count) / 4.0

    produce: list[str] = []
    meat_poultry: list[str] = []
    fish_seafood: list[str] = []
    refrigerated_eggs: list[str] = []
    pantry_spices: list[str] = []

    fetched_recipes: list[str] = []

    for r_id in recipe_ids:
        doc = await db.collection("recipes").document(r_id).get()
        if not doc.exists:
            continue
        data = doc.to_dict() or {}
        recipe_title = data.get("title", r_id)
        fetched_recipes.append(recipe_title)

        for raw_ing in data.get("ingredients", []):
            ing_lower = raw_ing.lower()
            formatted_item = f"{raw_ing} (scaled for {guest_count} guests: x{scale:.1f})"

            if any(k in ing_lower for k in ["onion", "potato", "carrot", "garlic", "herb", "parsley", "dill", "lemon", "rosemary", "thyme", "bay leaf", "celery", "squash", "zucchini"]):
                produce.append(formatted_item)
            elif any(k in ing_lower for k in ["chicken", "brisket", "flanken", "beef", "meat", "rib", "veal"]):
                meat_poultry.append(formatted_item)
            elif any(k in ing_lower for k in ["salmon", "fish", "cod", "halibut", "carp"]):
                fish_seafood.append(formatted_item)
            elif any(k in ing_lower for k in ["egg", "margarine", "butter", "mayo"]):
                refrigerated_eggs.append(formatted_item)
            else:
                pantry_spices.append(formatted_item)

    grocery_data = {
        "list_name": list_name,
        "guest_count": guest_count,
        "scale_multiplier": round(scale, 2),
        "recipes_included": fetched_recipes,
        "total_items": len(produce) + len(meat_poultry) + len(fish_seafood) + len(refrigerated_eggs) + len(pantry_spices),
        "aisles": {
            "Produce": produce,
            "Meat & Poultry": meat_poultry,
            "Fish": fish_seafood,
            "Refrigerated & Eggs": refrigerated_eggs,
            "Pantry & Seasonings": pantry_spices,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if save_to_firestore and fetched_recipes:
        slug = re.sub(r"[^a-z0-9]+", "-", list_name.lower()).strip("-")
        doc_id = f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"
        await db.collection("grocery_lists").document(doc_id).set(grocery_data)
        grocery_data["saved_document_id"] = doc_id

    return grocery_data


def calculate_blech_schedule(
    dishes: list[dict[str, Any]],
    candle_lighting_time: str,
    meal_times: list[dict[str, str]],
) -> dict[str, Any]:
    """Calculate blech placement timeline, heat zones, and liquid evaporation compensation.

    Args:
        dishes: List of dish dicts, each with keys 'name', 'max_warming_hours' (int), and 'meal' (str).
        candle_lighting_time: Time of candle lighting (e.g. '18:53' or '6:53 PM').
        meal_times: List of meals and planned eating times (e.g. [{'meal': 'Friday Night Dinner', 'time': '20:00'}, {'meal': 'Shabbat Lunch', 'time': '12:30'}]).

    Returns:
        Structured blech schedule with physical zones, evaporation compensation, and halachic cutoffs.
    """
    schedule_entries = []

    for dish in dishes:
        dish_name = dish.get("name", "Unknown Dish")
        target_meal = dish.get("meal", "First Meal")
        max_hours = dish.get("max_warming_hours", 18)

        # Estimate hours on heat based on meal sequence
        is_lunch = "lunch" in target_meal.lower() or "day" in target_meal.lower()
        is_day_two = "day 2" in target_meal.lower() or "second day" in target_meal.lower()

        if is_day_two:
            estimated_hours = 26
        elif is_lunch:
            estimated_hours = 18
        else:
            estimated_hours = 3

        # Physical Zone Determination
        dish_lower = dish_name.lower()
        if "kugel" in dish_lower or "pastry" in dish_lower:
            zone = "Perimeter (Gentle Keep-Warm Zone)"
            zone_tip = "Keep away from direct burner heat to prevent bottom scorching and crust drying."
        elif "soup" in dish_lower or "broth" in dish_lower:
            zone = "Center (Direct Heat Zone)"
            zone_tip = "Keep near burner center to ensure liquid remains piping hot (above Yad Soledet Bo)."
        elif estimated_hours >= 16:
            zone = "Mid-Blech (Moderate Indirect Zone)"
            zone_tip = "Position halfway between center and edge; turn dish 180 degrees before Chag begins if uneven."
        else:
            zone = "Center / Mid-Blech"
            zone_tip = "Standard placement; safe for shorter evening warming."

        # Evaporation Liquid Compensation
        if estimated_hours >= 20:
            compensation = "+3/4 to 1 cup additional braising broth; seal tightly with double heavy-duty aluminum foil."
        elif estimated_hours >= 12:
            compensation = "+1/2 cup additional braising liquid/sauce; crimp foil tightly around pan rim."
        else:
            compensation = "Standard recipe liquid is sufficient; ensure cover is sealed."

        # Durability assessment
        safe = estimated_hours <= max_hours
        status = "Within safe warming tolerance" if safe else f"WARNING: Estimated warming ({estimated_hours}h) exceeds recipe durability ({max_hours}h). Consider Day 2 chilled alternative or warming drawer lower setting."

        schedule_entries.append({
            "dish": dish_name,
            "target_meal": target_meal,
            "estimated_hours_on_blech": estimated_hours,
            "max_recipe_tolerance": max_hours,
            "status": status,
            "recommended_zone": zone,
            "zone_tip": zone_tip,
            "liquid_compensation": compensation,
        })

    return {
        "candle_lighting_deadline": candle_lighting_time,
        "halachic_readiness_checklist": [
            f"All dishes must be placed on the blech before candle lighting ({candle_lighting_time}).",
            "On Shabbat, all liquid food must be fully cooked (Ma'achal Ben Drusai / fully boiled) prior to placement.",
            "Knobs/controls must be covered (blech / tin foil / knob covers); no adjusting flame during Shabbat.",
            "If removing a pot on Shabbat intending to return it, keep hand on handle and do not set on counter (Chazarah rules).",
        ],
        "dishes_schedule": schedule_entries,
    }
