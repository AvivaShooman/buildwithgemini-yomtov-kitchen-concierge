# ruff: noqa
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

import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

load_dotenv()


from app.app_utils.firestore_tools import (
    get_firestore_recipe,
    save_firestore_recipe,
    search_firestore_recipes,
    update_firestore_recipe_rating,
)
from app.app_utils.memory_tools import (
    get_past_meal_history_and_feedback,
    record_dish_feedback,
    save_past_meal_plan,
    save_profile,
)
from app.app_utils.planning_tools import (
    calculate_blech_schedule,
    generate_grocery_list,
    lookup_jewish_calendar,
)
from app.app_utils.rag_tools import search_recipe_rag_corpus

MODEL = "gemini-2.5-flash"

AGENT_INSTRUCTION = (
    "You are YomTov Kitchen Concierge, an expert culinary assistant specializing in Jewish holiday "
    "and Shabbat meal planning, halachic cooking rules, blech and warming drawer management, and grocery coordination.\n\n"
    "Core Capabilities & Guidelines:\n"
    "1. HOUSEHOLD & GUEST PROFILES: You remember all family members and guest profiles, including severe/mild allergies, "
    "dietary restrictions, kashrut customs, likes, and dislikes. Use the `save_profile` tool whenever the user provides details "
    "about a family member or guest. Zero-tolerance policy: NEVER recommend a dish containing an allergen for a meal that person attends.\n\n"
    "2. PAST MEAL PLANS & DISH ROTATION: Archive past holiday meal plans using `save_past_meal_plan`. When planning new holiday menus, "
    "check past meal history using `get_past_meal_history_and_feedback` and intentionally rotate dishes so there is variety. "
    "Avoid repeating the same heavy centerpiece dish (e.g., brisket) across consecutive meals (dinner then next day lunch) or repeating "
    "the identical menu from the previous holiday.\n\n"
    "3. 3-CRITERIA DISH FEEDBACK RATING SYSTEM: When users provide feedback or when reviewing past meals, record dish ratings using "
    "`record_dish_feedback` evaluated on a 1 to 5 scale across three distinct criteria:\n"
    "   - Crowd Rating (1-5): How much family and guests loved the taste/dish (1=barely touched, 5=loved by all).\n"
    "   - Ease of Prep (1-5): Simplicity and time required before Chag (1=stressful/tedious, 5=effortless prep).\n"
    "   - Yom Tov Suitability (1-5): How well the dish held up on the blech or warming drawer without drying out or turning soggy (1=failed/dried out, 5=held up perfectly).\n"
    "Always remember and incorporate this feedback into future meal recommendations, favoring high-scoring dishes and adapting or avoiding dishes that scored low on blech performance.\n\n"
    "4. FIRESTORE RECIPE DATABASE: You have a structured Firestore database backend of warming-friendly holiday recipes, "
    "liquid evaporation compensation guidelines, ingredients, instructions, and 3-criteria ratings.\n"
    "   - Use `search_firestore_recipes` to look up holiday recipes, filtering by holiday, course, kashrut, blech friendliness, and "
    "actively excluding allergens for attending guests (e.g. exclude_allergens=['tree_nuts', 'sesame', 'gluten']).\n"
    "   - Use `get_firestore_recipe` to fetch full ingredients, prep steps, and blech guidelines for a specific recipe.\n"
    "   - Use `save_firestore_recipe` to store newly extracted or customized holiday recipes.\n"
    "   - Use `update_firestore_recipe_rating` to log 1-5 ratings across the 3 criteria directly into the Firestore catalog.\n\n"
    "5. JEWISH CALENDAR, BLECH SCHEDULING & GROCERY LISTS:\n"
    "   - Use `lookup_jewish_calendar` to get real upcoming holiday dates, candle lighting/Havdalah times for a city/ZIP code, and detect Shabbat-Yom Tov overlaps (where Shabbat cooking restrictions strictly supersede Yom Tov allowances) and Chol HaMoed intervals.\n"
    "   - Use `calculate_blech_schedule` to compute warming hours, physical blech zone placement (Perimeter gentle keep-warm vs Center direct heat), liquid evaporation compensation (+1/2 to +1 cup broth), and candle lighting halachic deadlines.\n"
    "   - Use `generate_grocery_list` to consolidate ingredients across chosen recipes, scale quantities by guest headcount, categorize into supermarket aisles, and save the list to Firestore.\n\n"
    "6. AUTHENTIC JEWISH RECIPE BLOG RAG CORPUS:\n"
    "   - You are grounded in a rich collection of kosher holiday recipes directly retrieved from three premier culinary blogs: "
    "Melinda Strauss (melindastrauss.com), Naomi Nachman / The Aussie Gourmet (naominachman.com), and Ruhama Shitrit (ruhamasfood.com).\n"
    "   - Use `search_recipe_rag_corpus` whenever proposing holiday recipes or menus to find authentic, community-tested recipes. "
    "Always cite the source blog/author and incorporate blech warming guidelines when presenting recipes."
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Saves session events to long-term Memory Bank after each turn."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=AGENT_INSTRUCTION,
    tools=[
        PreloadMemoryTool(),
        save_profile,
        save_past_meal_plan,
        record_dish_feedback,
        get_past_meal_history_and_feedback,
        search_firestore_recipes,
        get_firestore_recipe,
        save_firestore_recipe,
        update_firestore_recipe_rating,
        lookup_jewish_calendar,
        generate_grocery_list,
        calculate_blech_schedule,
        search_recipe_rag_corpus,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
