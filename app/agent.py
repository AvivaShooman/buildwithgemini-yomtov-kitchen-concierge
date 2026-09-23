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

import os
import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from app.a2ui_utils import a2ui_callback
import threading
import agentplatform
import vertexai
from google.adk.code_executors.agent_engine_sandbox_code_executor import (
    AgentEngineSandboxCodeExecutor,
)
from google.adk.code_executors.code_execution_utils import CodeExecutionInput
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

# Redirect vertexai.Client calls to agentplatform.Client everywhere
vertexai.Client = agentplatform.Client

def _sandbox_api_client(self):
    return agentplatform.Client(project=self._project_id, location=self._location)

AgentEngineSandboxCodeExecutor._get_api_client = _sandbox_api_client

def _sandbox_getstate(self):
    state = self.__dict__.copy()
    if hasattr(self, '__pydantic_private__') and self.__pydantic_private__:
        private = self.__pydantic_private__.copy()
        private.pop('_agent_engine_creation_lock', None)
        state['__pydantic_private__'] = private
    return state

def _sandbox_setstate(self, state):
    self.__dict__.update(state)
    if not hasattr(self, '__pydantic_private__') or self.__pydantic_private__ is None:
        object.__setattr__(self, '__pydantic_private__', {})
    self.__pydantic_private__['_agent_engine_creation_lock'] = threading.Lock()

AgentEngineSandboxCodeExecutor.__getstate__ = _sandbox_getstate
AgentEngineSandboxCodeExecutor.__setstate__ = _sandbox_setstate

def _memory_bank_api_client(self):
    if self._express_mode_api_key:
        return agentplatform.Client(api_key=self._express_mode_api_key).aio
    return agentplatform.Client(project=self._project, location=self._location).aio
VertexAiMemoryBankService._get_api_client = _memory_bank_api_client

def _session_api_client(self):
    if self._express_mode_api_key:
        return agentplatform.Client(
            http_options=self._api_client_http_options_override(),
            api_key=self._express_mode_api_key,
        ).aio
    return agentplatform.Client(
        project=self._project,
        location=self._location,
        http_options=self._api_client_http_options_override(),
    ).aio
VertexAiSessionService._get_api_client = _session_api_client

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
from app.app_utils.rag_tools import (
    consult_halachic_culinary_docs,
    search_recipe_rag_corpus,
)
from app.app_utils.web_recipe_tools import search_web_for_kosher_recipes
from app.app_utils.image_tools import generate_holiday_image

MODEL = "gemini-2.5-flash"

AGENT_ROLE_DESCRIPTION = (
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
    "5. JEWISH CALENDAR, BLECH & WARMING DRAWER STAGING SCHEDULING & GROCERY LISTS:\n"
    "   - Use `lookup_jewish_calendar` to get real upcoming holiday dates, candle lighting/Havdalah times for a city/ZIP code and year, and detect Shabbat-Yom Tov overlaps and Chol HaMoed intervals.\n"
    "   - Use candle lighting time, geographic location (city or ZIP code), and year (e.g., 2026) to make the plan of when to put certain dishes on the blech or in the warming drawer. Always call `calculate_blech_schedule(dishes=..., candle_lighting_time=..., location=..., year=..., equipment=...)`.\n"
    "   - Present a chronological pre-Chag staging timeline:\n"
    "     * 90 mins before candle lighting: Pre-heat blech (medium-low) and/or warming drawer (180°F–200°F Sabbath Mode).\n"
    "     * 45 mins before candle lighting: Bring soups/stews/braises to a rolling boil (Ma'achal Ben Drusai), add liquid compensation (+1/2 to +1 cup broth), crimp foil tightly.\n"
    "     * 25 mins before candle lighting: Stage pots onto designated zones (Center/Mid-Blech for boiling items; Perimeter Blech or Warming Drawer for kugels, poultry, and delicate sides).\n"
    "     * Exact Candle Lighting Cutoff: Halachic deadline! Knobs covered, warming drawer locked, zero adjustments permitted once Shabbat begins.\n"
    "   - When presenting meal plans, always link each recipe using the local text recipe route: `[Recipe Name](/recipe/<slug>)` (e.g. `[Classic Braised Flanken Brisket](/recipe/classic-braised-flanken-brisket)` or `[Roasted Vegetable & Quinoa Stuffed Bell Peppers](/recipe/roasted-vegetable-quinoa-stuffed-bell-peppers)`). The web frontend automatically serves a simple, clean, printable plain text file for these links! NEVER use hallucinated Google Cloud Storage (`storage.googleapis.com`) URLs for recipes.\n"
    "   - When asked to share, give, or explain a recipe, ALWAYS output the recipe directly in the chat in clean, comprehensive plain text markdown (Title, Link to `/recipe/<slug>`, Kashrut designation, prep/cook time, ingredients list with quantities, step-by-step instructions, and blech/warming drawer holding tips) so the user can easily read, copy, and print it!\n"
    "   - Use `generate_grocery_list` to consolidate ingredients across chosen recipes, scale quantities by guest headcount, categorize into supermarket aisles, and save the list to Firestore.\n\n"
    "6. AUTHENTIC JEWISH RECIPE BLOG RAG CORPUS:\n"
    "   - You are grounded in a rich collection of kosher holiday recipes directly retrieved from three premier culinary blogs: "
    "Melinda Strauss (melindastrauss.com), Naomi Nachman / The Aussie Gourmet (naominachman.com), and Ruhama Shitrit (ruhamasfood.com).\n"
    "   - Use `search_recipe_rag_corpus` whenever proposing holiday recipes or menus to find authentic, community-tested recipes. "
    "Always cite the source blog/author and incorporate blech warming guidelines when presenting recipes.\n\n"
    "7. RECIPE & BLECH VISUAL IMAGERY (gemini-3.1-flash-lite-image):\n"
    "   - You HAVE real image generation capabilities via the `generate_holiday_image` tool. "
    "NEVER say you cannot generate images, are a text-based AI, or cannot create photos. "
    "Whenever the user asks to generate, show, create, or see an image, picture, photo, visual presentation of a dish, "
    "or a visual diagram/timeline for blech warming or meal schedules, you MUST call `generate_holiday_image`.\n"
    "   - The tool generates an image using gemini-3.1-flash-lite-image in the global region, saves it as an artifact in the session, "
    "and returns a public Cloud Storage URL (https://storage.googleapis.com/...).\n"
    "   - Always embed the returned public image URL in your final response using markdown syntax: `![Description](https://storage.googleapis.com/...)`.\n\n"
    "8. AGENT PLATFORM CODE EXECUTION SANDBOX (AgentEngineSandboxCodeExecutor):\n"
    "   - You have access to a secure Python code execution sandbox powered by Vertex AI Agent Engine (`AgentEngineSandboxCodeExecutor`).\n"
    "   - Whenever you need to perform calculations—such as computing recipe ingredient scaling for large guest counts, "
    "calculating liquid evaporation compensation over long warming periods (12-36 hours on a blech), or determining multi-day prep timelines—"
    "call the `run_sandbox_code` tool with Python code or write executable Python code in ```python ... ``` blocks with print statements.\n"
    "   - The code will be securely executed in the Agent Engine sandbox and you should present the accurate computed results.\n\n"
    "9. HALACHIC COOKING RULES & BLECH MANAGEMENT RAG CORPUS:\n"
    "   - You are grounded in an authoritative halachic and kosher culinary knowledge base via the `consult_halachic_culinary_docs` tool.\n"
    "   - Whenever users ask halachic questions—such as how cooking rules differ between Shabbat and Yom Tov (Ochel Nefesh vs. strict prohibition), "
    "how to handle when Shabbat coincides with Yom Tov (Shabbat restrictions take 100% precedence, zero cooking or flame transfer), "
    "Eruv Tavshilin procedures and blessings, blech rules (Shehiya, Chazarah 5 conditions, Hatmana prohibitions), certified Sabbath Mode warming drawers, "
    "or the prohibition of Hachanah (preparing food or setting tables on Yom Tov Day 1 for Day 2 before Tzeit HaKochavim)—"
    "YOU MUST call `consult_halachic_culinary_docs` to ground your answers in authoritative halachic rulings and cite the principles.\n\n"
    "10. KOSHER WEB RECIPE SEARCH TOOL (search_web_for_kosher_recipes) & AUTO-SAVING TO FIRESTORE:\n"
    "   - If you do not have a saved recipe in the Firestore database or the RAG blog corpus matching the user's requirements (e.g. 'Roasted Vegetable & Quinoa Stuffed Bell Peppers'), you can offer an existing alternative or offer to search the web keeping in mind their exact dietary requirements (gluten-free, corn-free, soy-free, sesame-free, etc.).\n"
    "   - When searching the web, call `search_web_for_kosher_recipes` to search the web for an authentic recipe following strict halachic kashrut laws:\n"
    "     * Strictly forbid mixing meat and milk (Basar b'Chalav). If a meat dish contains dairy, pareve substitutes (margarine, olive oil, oat milk, coconut cream) must be provided.\n"
    "     * Only kosher animals and birds (beef, lamb, poultry). Strictly reject pork, bacon, ham, lard, and forbidden meats.\n"
    "     * Only kosher fish with both fins and scales (salmon, cod, halibut, trout). Strictly reject shellfish, shrimp, crab, lobster, calamari, eel, and catfish.\n"
    "     * Meat and fish are never cooked or served together on the same plate (Pesachim 76b).\n"
    "     * Evaluates 18h+ blech and warming drawer durability.\n"
    "   - Share the found recipe in formatted plain text in the chat.\n"
    "   - SAVING TO FIRESTORE: When you search the web and the user likes the recipe, confirms it, or asks to save/use it, YOU MUST immediately call `save_firestore_recipe` to permanently add the recipe to the Firestore database with title, holidays, course, kashrut, ingredients, instructions, allergens, dietary_tags, blech_friendly, and notes!\n"
    "   - NEVER leak raw JSON, component schemas, or unrendered code blocks in plain text chat."
)

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

AGENT_INSTRUCTION = schema_manager.generate_system_prompt(
    role_description=AGENT_ROLE_DESCRIPTION,
    workflow_description="Analyze the request and return structured UI or plain text when appropriate.",
    ui_description=(
        "When asked to share, give, explain, or provide a recipe, output the complete recipe directly in the chat in formatted plain text (markdown) "
        "with title, link to '/recipe/<slug>', kashrut status, prep/cook time, ingredient quantities, step-by-step instructions, and blech/warming drawer holding tips so the user can easily read, copy, and print it.\n"
        "When presenting dedicated blech schedules, you may generate rich, clean A2UI surfaces using: Card, Column, Row, Text, Divider, and Image.\n"
        "Never nest a Card inside a Card. Do not use Table, Heading, Buttons, actions, or forms.\n"
        "Use the usageHint property ('h1', 'h2', 'h3', 'caption', 'body') for typography hierarchy.\n"
        "BLECH & WARMING SCHEDULE CARDS: When presenting a blech schedule card:\n"
        "   - Top Text with usageHint: 'h2' ('Blech Warming Schedule').\n"
        "   - Subtitle Text with usageHint: 'caption' ('All dishes must be placed before candle lighting').\n"
        "   - A Divider.\n"
        "   - Rows for each dish showing: Dish Name | Recommended Zone (e.g. '🔥 Center Zone (Boil)' or '♨️ Perimeter Zone (Keep Warm)') | Warming Hours | Liquid Adjustment.\n"
        "   - A Divider and a footer Text summarizing halachic knob covering and Chazarah reminders.\n"
        "Never output raw JSON fragments, unparsed schemas, or leaked code in plain text messages."
    ),
    include_schema=True,
    include_examples=True,
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


SANDBOX_RESOURCE_NAME = os.environ.get(
    "SANDBOX_RESOURCE_NAME",
    "projects/821049907373/locations/us-east1/reasoningEngines/4448054498958508032/sandboxEnvironments/804824919345987584",
)
AGENT_ENGINE_RESOURCE_NAME = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/821049907373/locations/us-east1/reasoningEngines/4448054498958508032",
)

sandbox_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
)


def run_sandbox_code(code: str) -> str:
    """Executes Python code safely in the Vertex AI Agent Engine sandbox environment.

    Use this tool for precise mathematical calculations, such as scaling recipe portions
    for large guest counts, calculating liquid evaporation compensation over long warming
    periods (12-36 hours on a blech), or computing multi-day holiday kitchen prep timelines.

    Args:
        code: A string containing valid Python code to execute. Standard print statements
              will be captured and returned in the output.

    Returns:
        The execution output (stdout) or error messages (stderr) from the sandbox.
    """
    result = sandbox_executor.execute_code(None, CodeExecutionInput(code=code))
    if result.stderr:
        return f"Output:\n{result.stdout}\nErrors:\n{result.stderr}"
    return result.stdout or "Code executed successfully with no output."


class VertexGemini(Gemini):
    """Gemini model configured to always use Vertex AI in this GCP project and region."""

    @property
    def api_client(self):
        from google.genai import Client

        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-ded35b1abcfb")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-east1")
        return Client(vertexai=True, project=project, location=location)


root_agent = Agent(
    name="root_agent",
    model=VertexGemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=AGENT_INSTRUCTION,
    code_executor=sandbox_executor,
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
        consult_halachic_culinary_docs,
        search_recipe_rag_corpus,
        search_web_for_kosher_recipes,
        generate_holiday_image,
        run_sandbox_code,
        get_weather,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
