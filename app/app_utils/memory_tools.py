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

import logging
from typing import Sequence
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.tools import ToolContext
from google.genai import types

logger = logging.getLogger(__name__)


def _validate_rating(name: str, val: int) -> int:
    """Validates that a rating is an integer between 1 and 5 inclusive."""
    try:
        val_int = int(val)
    except (TypeError, ValueError):
        raise ValueError(f"Rating '{name}' must be an integer between 1 and 5.")
    if val_int < 1 or val_int > 5:
        raise ValueError(f"Rating '{name}' must be between 1 and 5 (got {val_int}).")
    return val_int


async def save_profile(
    name: str,
    is_guest: bool,
    allergies: Sequence[str] | None = None,
    dietary_restrictions: Sequence[str] | None = None,
    likes: Sequence[str] | None = None,
    dislikes: Sequence[str] | None = None,
    notes: str = "",
    tool_context: ToolContext | None = None,
) -> str:
    """Saves or updates a household member or guest dietary profile into long-term memory.

    Args:
        name: Name of the individual (e.g. 'Uncle Dan', 'Leah', 'Grandma Sarah').
        is_guest: True if this person is an invited guest, False if a household family member.
        allergies: List of allergies (e.g. ['tree nuts', 'sesame', 'shellfish', 'dairy']).
        dietary_restrictions: List of dietary restrictions (e.g. ['gluten-free', 'vegetarian', 'low-sodium']).
        likes: Favorite foods or culinary preferences (e.g. ['slow-cooked meats', 'brisket', 'sweet kugels']).
        dislikes: Disliked foods or ingredients (e.g. ['mushrooms', 'cilantro', 'overly sweet wine']).
        notes: Any additional notes, kashrut customs, or details (e.g. 'Prefers Gebrochts-free on Pesach').
        tool_context: Tool execution context injected by ADK.

    Returns:
        Confirmation message detailing the saved profile.
    """
    role_label = "GUEST" if is_guest else "HOUSEHOLD MEMBER"
    allergies_list = list(allergies or [])
    restrictions_list = list(dietary_restrictions or [])
    likes_list = list(likes or [])
    dislikes_list = list(dislikes or [])

    allergies_str = ", ".join(allergies_list) if allergies_list else "None reported"
    restrictions_str = ", ".join(restrictions_list) if restrictions_list else "None"
    likes_str = ", ".join(likes_list) if likes_list else "None specified"
    dislikes_str = ", ".join(dislikes_list) if dislikes_list else "None specified"

    memory_text = (
        f"[{role_label} PROFILE] Name: {name}. "
        f"Allergies: {allergies_str}. "
        f"Dietary Restrictions: {restrictions_str}. "
        f"Likes: {likes_str}. "
        f"Dislikes: {dislikes_str}. "
    )
    if notes:
        memory_text += f"Notes: {notes.strip()}. "

    if tool_context and hasattr(tool_context, "add_memory"):
        try:
            entry = MemoryEntry(
                content=types.Content(parts=[types.Part.from_text(text=memory_text)])
            )
            await tool_context.add_memory(memories=[entry])
        except Exception as e:
            logger.warning("Could not persist profile memory entry directly: %s", e)

    return f"Successfully saved profile for {name} ({role_label}): Allergies: {allergies_str}; Restrictions: {restrictions_str}."


async def save_past_meal_plan(
    holiday: str,
    year: int,
    meal_name: str,
    dishes: Sequence[str],
    guests: Sequence[str] | None = None,
    notes: str = "",
    tool_context: ToolContext | None = None,
) -> str:
    """Archives a past Yom Tov or Shabbat meal plan into long-term memory to enable dish rotation and avoid repetition.

    Args:
        holiday: Name of the holiday or occasion (e.g. 'Rosh Hashanah', 'Pesach', 'Sukkot', 'Shavuot', 'Shabbat').
        year: The calendar year (e.g. 2025, 2026, 5786).
        meal_name: Meal slot (e.g. 'Night 1 Dinner', 'Day 1 Lunch', 'Day 2 Dinner', 'Chol HaMoed Lunch').
        dishes: List of dishes served (e.g. ['Honey-braised Brisket', 'Potato Kugel', 'Tzimmes', 'Chicken Soup']).
        guests: Names of guests who attended the meal.
        notes: General observations or context (e.g. 'Food was sufficient, leftovers lasted through Day 2').
        tool_context: Tool execution context injected by ADK.

    Returns:
        Confirmation message detailing the saved meal plan.
    """
    dishes_list = list(dishes or [])
    guests_list = list(guests or [])
    dishes_str = ", ".join(dishes_list) if dishes_list else "None listed"
    guests_str = ", ".join(guests_list) if guests_list else "Family only"

    memory_text = (
        f"[PAST MEAL PLAN] {holiday} {year} - {meal_name}. "
        f"Dishes Served: {dishes_str}. "
        f"Attendees: {guests_str}. "
    )
    if notes:
        memory_text += f"Notes: {notes.strip()}. "

    if tool_context and hasattr(tool_context, "add_memory"):
        try:
            entry = MemoryEntry(
                content=types.Content(parts=[types.Part.from_text(text=memory_text)])
            )
            await tool_context.add_memory(memories=[entry])
        except Exception as e:
            logger.warning("Could not persist meal plan memory entry directly: %s", e)

    return f"Archived meal plan for {holiday} {year} ({meal_name}): {len(dishes_list)} dishes recorded for dish rotation."


async def record_dish_feedback(
    dish_name: str,
    holiday_or_meal: str,
    crowd_rating: int,
    ease_of_prep: int,
    yomtov_suitability: int,
    notes: str = "",
    tool_context: ToolContext | None = None,
) -> str:
    """Records post-holiday ratings and feedback for a specific dish across 3 criteria (1-5 scale) into long-term memory.

    Args:
        dish_name: Name of the dish (e.g. 'Slow-Cooker Pomegranate Short Ribs', 'Sweet Potato Kugel').
        holiday_or_meal: Holiday or meal when served (e.g. 'Rosh Hashanah 2025 Dinner', 'Pesach Seder').
        crowd_rating: 1-5 rating on how much family and guests loved it (1=nobody ate it, 5=everyone loved it / empty platter).
        ease_of_prep: 1-5 rating on preparation simplicity (1=labor-intensive/stressful, 5=quick and effortless).
        yomtov_suitability: 1-5 rating on Yom Tov/blech/warming drawer performance (1=dried out/soggy/burned, 5=held up perfectly on blech/warming drawer for 12-24h).
        notes: Qualitative feedback, tips for next time, adjustments needed (e.g. 'Add 1/2 cup extra broth next time to prevent drying').
        tool_context: Tool execution context injected by ADK.

    Returns:
        Confirmation message summarizing the recorded rating and feedback.
    """
    crowd = _validate_rating("crowd_rating", crowd_rating)
    prep = _validate_rating("ease_of_prep", ease_of_prep)
    yt = _validate_rating("yomtov_suitability", yomtov_suitability)

    memory_text = (
        f"[DISH FEEDBACK] Dish: {dish_name} ({holiday_or_meal}). "
        f"Crowd Rating: {crowd}/5. "
        f"Ease of Prep: {prep}/5. "
        f"Yom Tov Suitability: {yt}/5. "
    )
    if notes:
        memory_text += f"Notes: {notes.strip()}. "

    if tool_context and hasattr(tool_context, "add_memory"):
        try:
            entry = MemoryEntry(
                content=types.Content(parts=[types.Part.from_text(text=memory_text)])
            )
            await tool_context.add_memory(memories=[entry])
        except Exception as e:
            logger.warning("Could not persist dish feedback memory entry directly: %s", e)

    return (
        f"Recorded feedback for '{dish_name}' ({holiday_or_meal}): "
        f"Crowd: {crowd}/5, Prep: {prep}/5, Yom Tov / Blech: {yt}/5. "
        f"Stored in memory for future menu planning."
    )


async def get_past_meal_history_and_feedback(
    query: str,
    tool_context: ToolContext | None = None,
) -> str:
    """Searches long-term memory for past holiday meal plans, dish rotation records, guest profiles, and dish feedback ratings.

    Args:
        query: Search query (e.g. 'brisket feedback', 'Pesach 2025 meal plan', 'Uncle Dan allergies', 'dishes rated 5').
        tool_context: Tool execution context injected by ADK.

    Returns:
        Matching memories and history from the memory bank.
    """
    if not tool_context or not hasattr(tool_context, "search_memory"):
        return f"Memory service search not available in this context for query: {query}."

    try:
        response = await tool_context.search_memory(query=query)
        if not response or not getattr(response, "memories", None):
            return f"No memories found matching query: '{query}'."

        results = []
        for idx, mem in enumerate(response.memories, 1):
            if mem.content and mem.content.parts:
                for part in mem.content.parts:
                    if part.text:
                        results.append(f"{idx}. {part.text}")
        if not results:
            return f"No text content found in memories matching '{query}'."
        return "Found matching memories:\n" + "\n".join(results)
    except Exception as e:
        logger.warning("Failed to search memory: %s", e)
        return f"Error searching memory for '{query}': {e}"
