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

"""Firestore database tools for YomTov Kitchen Concierge recipes and ratings.

CRITICAL REQUIREMENT:
The GCP Project ID is hardcoded as a string constant to prevent Agent Platform
from resolving the numeric project number (821049907373), which causes Firestore
permission and routing failures in deployed environments.
"""

from __future__ import annotations

import asyncio
import datetime
import re
from typing import Any

from google.cloud import firestore

# Hardcoded project ID as required per platform constraints
PROJECT_ID = "qwiklabs-gcp-04-ded35b1abcfb"
COLLECTION_NAME = "recipes"

_client: firestore.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def get_firestore_client() -> firestore.AsyncClient:
    """Returns an AsyncClient connected to the hardcoded Firestore project bound to the running loop."""
    global _client, _client_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _client is None or _client_loop != current_loop:
        _client = firestore.AsyncClient(project=PROJECT_ID)
        _client_loop = current_loop
    return _client


def _slugify(text: str) -> str:
    """Convert title to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


def _validate_rating(rating_name: str, val: int) -> int:
    """Ensure rating is an integer between 1 and 5."""
    try:
        int_val = int(val)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{rating_name} must be an integer between 1 and 5.") from exc
    if not (1 <= int_val <= 5):
        raise ValueError(f"{rating_name} must be between 1 and 5 (got {int_val}).")
    return int_val


async def search_firestore_recipes(
    holiday: str | None = None,
    course: str | None = None,
    kashrut: str | None = None,
    blech_friendly: bool | None = None,
    max_warming_hours: int | None = None,
    exclude_allergens: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search recipes in the Firestore database matching holiday, dietary, and warming criteria.

    Args:
        holiday: Optional holiday filter (e.g. 'Pesach', 'Rosh Hashanah', 'Sukkot', 'Shabbat', 'Chol HaMoed').
        course: Optional course filter ('main', 'side', 'fish', 'soup', 'dessert').
        kashrut: Optional kashrut classification ('meat', 'dairy', 'pareve').
        blech_friendly: If True, only returns dishes suitable for extended blech warming.
        max_warming_hours: Minimum hours the dish must tolerate warming (e.g. 18 for a 3-day Yom Tov).
        exclude_allergens: List of allergen strings to exclude (e.g. ['tree_nuts', 'sesame', 'gluten']).
            Any recipe containing any of these allergens is filtered out.

    Returns:
        List of matching recipe summary dictionaries.
    """
    db = get_firestore_client()
    query = db.collection(COLLECTION_NAME)

    docs = [doc async for doc in query.stream()]
    results = []

    normalized_exclude = [a.lower().strip() for a in (exclude_allergens or [])]
    normalized_holiday = holiday.lower().strip() if holiday else None
    normalized_course = course.lower().strip() if course else None
    normalized_kashrut = kashrut.lower().strip() if kashrut else None

    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id

        # Holiday check
        if normalized_holiday:
            doc_holidays = [h.lower() for h in data.get("holidays", [])]
            if not any(normalized_holiday in h for h in doc_holidays):
                continue

        # Course check
        if normalized_course and data.get("course", "").lower() != normalized_course:
            continue

        # Kashrut check
        if normalized_kashrut and data.get("kashrut", "").lower() != normalized_kashrut:
            continue

        # Blech friendly check
        if blech_friendly is not None and data.get("blech_friendly") != blech_friendly:
            continue

        # Max warming hours check
        if max_warming_hours is not None:
            if data.get("max_warming_hours", 0) < max_warming_hours:
                continue

        # Allergen exclusion check (zero tolerance for excluded allergens)
        if normalized_exclude:
            doc_allergens = [a.lower() for a in data.get("allergens", [])]
            has_allergen = False
            for excl in normalized_exclude:
                if any(excl in da for da in doc_allergens):
                    has_allergen = True
                    break
            if has_allergen:
                continue

        results.append({
            "id": data["id"],
            "title": data.get("title", ""),
            "holidays": data.get("holidays", []),
            "course": data.get("course", ""),
            "kashrut": data.get("kashrut", ""),
            "blech_friendly": data.get("blech_friendly", False),
            "warming_drawer_friendly": data.get("warming_drawer_friendly", False),
            "max_warming_hours": data.get("max_warming_hours", 0),
            "evaporation_compensation": data.get("evaporation_compensation", ""),
            "day2_leftover_quality": data.get("day2_leftover_quality", ""),
            "allergens": data.get("allergens", []),
            "dietary_tags": data.get("dietary_tags", []),
            "ratings": data.get("ratings", {}),
            "notes": data.get("notes", ""),
        })

    return results


async def get_firestore_recipe(recipe_id: str) -> dict[str, Any]:
    """Retrieve complete recipe details including ingredients and prep instructions from Firestore.

    Args:
        recipe_id: Unique slug ID of the recipe (e.g. 'classic-braised-flanken-brisket').

    Returns:
        Dictionary containing recipe fields or error message if not found.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(recipe_id)
    doc = await doc_ref.get()

    if not doc.exists:
        return {"error": f"Recipe with ID '{recipe_id}' not found in Firestore."}

    data = doc.to_dict() or {}
    data["id"] = doc.id
    return data


async def save_firestore_recipe(
    title: str,
    holidays: list[str],
    course: str,
    kashrut: str,
    ingredients: list[str],
    instructions: str,
    allergens: list[str] | None = None,
    dietary_tags: list[str] | None = None,
    blech_friendly: bool = True,
    warming_drawer_friendly: bool = True,
    max_warming_hours: int = 18,
    evaporation_compensation: str = "",
    day2_leftover_quality: str = "Good",
    crowd_rating: float = 5.0,
    ease_of_prep: float = 4.0,
    yomtov_suitability: float = 5.0,
    notes: str = "",
) -> dict[str, Any]:
    """Save a new extracted or user-provided recipe into Firestore.

    Args:
        title: Title of the dish (e.g. 'Braised Short Ribs').
        holidays: Relevant Jewish holidays (e.g. ['Rosh Hashanah', 'Sukkot', 'Pesach']).
        course: Course classification ('main', 'side', 'fish', 'soup', 'dessert').
        kashrut: 'meat', 'dairy', or 'pareve'.
        ingredients: List of ingredients with quantities.
        instructions: Preparation and reheating instructions.
        allergens: List of allergens in dish (e.g. ['gluten', 'tree_nuts', 'sesame']).
        dietary_tags: Dietary tags (e.g. ['gluten-free', 'nut-free', 'celiac-safe']).
        blech_friendly: Whether dish tolerates long blech warming without burning.
        warming_drawer_friendly: Whether dish can sit in warming drawer safely.
        max_warming_hours: Maximum hours dish can stay warm.
        evaporation_compensation: Liquid adjustment needed for extended heat.
        day2_leftover_quality: Assessment of how dish tastes reheated on Day 2.
        crowd_rating: Initial crowd/taste rating (1.0 - 5.0).
        ease_of_prep: Initial ease of preparation rating (1.0 - 5.0).
        yomtov_suitability: Initial Yom Tov / warming durability rating (1.0 - 5.0).
        notes: Halachic notes, heat zone placement, or serving advice.

    Returns:
        Dictionary confirming document creation with the generated recipe ID.
    """
    doc_id = _slugify(title)
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(doc_id)

    payload = {
        "title": title,
        "holidays": holidays,
        "course": course.lower(),
        "kashrut": kashrut.lower(),
        "ingredients": ingredients,
        "instructions": instructions,
        "allergens": allergens or [],
        "dietary_tags": dietary_tags or [],
        "blech_friendly": blech_friendly,
        "warming_drawer_friendly": warming_drawer_friendly,
        "max_warming_hours": max_warming_hours,
        "evaporation_compensation": evaporation_compensation,
        "day2_leftover_quality": day2_leftover_quality,
        "ratings": {
            "crowd_rating": round(float(crowd_rating), 1),
            "ease_of_prep": round(float(ease_of_prep), 1),
            "yomtov_suitability": round(float(yomtov_suitability), 1),
            "review_count": 1,
        },
        "feedback_history": [
            {
                "crowd_rating": round(float(crowd_rating), 1),
                "ease_of_prep": round(float(ease_of_prep), 1),
                "yomtov_suitability": round(float(yomtov_suitability), 1),
                "notes": notes or "Initial recipe entry",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        ],
        "notes": notes,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    await doc_ref.set(payload)
    return {
        "status": "success",
        "recipe_id": doc_id,
        "title": title,
        "message": f"Recipe '{title}' saved to Firestore with ID '{doc_id}'.",
    }


async def update_firestore_recipe_rating(
    recipe_id: str,
    crowd_rating: int,
    ease_of_prep: int,
    yomtov_suitability: int,
    notes: str = "",
) -> dict[str, Any]:
    """Update ratings for a recipe in Firestore across the 3 criteria (1-5 scale) and recalculate averages.

    Args:
        recipe_id: Unique slug ID of the recipe (e.g. 'classic-braised-flanken-brisket').
        crowd_rating: Integer rating from 1 to 5 for crowd liking and taste.
        ease_of_prep: Integer rating from 1 to 5 for ease of preparation.
        yomtov_suitability: Integer rating from 1 to 5 for blech / warming drawer performance.
        notes: Optional feedback notes (e.g. 'Dried out after 18h', 'Sauce thickened perfectly').

    Returns:
        Updated ratings dictionary or error if recipe does not exist.
    """
    valid_crowd = _validate_rating("crowd_rating", crowd_rating)
    valid_ease = _validate_rating("ease_of_prep", ease_of_prep)
    valid_yomtov = _validate_rating("yomtov_suitability", yomtov_suitability)

    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(recipe_id)
    doc = await doc_ref.get()

    if not doc.exists:
        return {"error": f"Recipe '{recipe_id}' does not exist in Firestore."}

    data = doc.to_dict() or {}
    ratings = data.get("ratings", {})
    count = ratings.get("review_count", 0)

    old_crowd = ratings.get("crowd_rating", valid_crowd)
    old_ease = ratings.get("ease_of_prep", valid_ease)
    old_yomtov = ratings.get("yomtov_suitability", valid_yomtov)

    new_count = count + 1
    new_crowd = round(((old_crowd * count) + valid_crowd) / new_count, 1)
    new_ease = round(((old_ease * count) + valid_ease) / new_count, 1)
    new_yomtov = round(((old_yomtov * count) + valid_yomtov) / new_count, 1)

    new_ratings = {
        "crowd_rating": new_crowd,
        "ease_of_prep": new_ease,
        "yomtov_suitability": new_yomtov,
        "review_count": new_count,
    }

    feedback_entry = {
        "crowd_rating": valid_crowd,
        "ease_of_prep": valid_ease,
        "yomtov_suitability": valid_yomtov,
        "notes": notes,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    feedback_history = data.get("feedback_history", [])
    feedback_history.append(feedback_entry)

    await doc_ref.update({
        "ratings": new_ratings,
        "feedback_history": feedback_history,
    })

    return {
        "status": "success",
        "recipe_id": recipe_id,
        "title": data.get("title", recipe_id),
        "updated_ratings": new_ratings,
        "message": f"Updated ratings for '{data.get('title', recipe_id)}' (Reviews: {new_count}).",
    }
