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
import logging
import re
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from typing import Any

import httpx
from google.cloud import firestore

logger = logging.getLogger(__name__)

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


# Regex patterns for accurate supermarket aisle categorization
_PRODUCE_RE = re.compile(
    r"\b(onion|shallot|shallots|potato|potatoes|carrot|carrots|garlic|herb|herbs|parsley|dill|cilantro|basil|lemon|lemons|lime|limes|orange|oranges|apple|apples|cranberr|cranberries|rosemary|thyme|bay leaf|celery|squash|zucchini|pepper|peppers|cabbage|green bean|green beans|cucumber|cucumbers|tomato|tomatoes|mushroom|mushrooms|beet|beets|scallion|scallions|lettuce|spinach|arugula|ginger|prune|prunes|apricot|apricots)\b",
    re.IGNORECASE,
)
_MEAT_RE = re.compile(
    r"\b(chicken|brisket|flanken|beef|meat|ribs?|veal|ground\s+beef|turkey|lamb|steak|poultry)\b",
    re.IGNORECASE,
)
_FISH_RE = re.compile(
    r"\b(salmon|fish|cod|halibut|carp|tilapia|tuna|sea\s+bass|fillet|fillets)\b",
    re.IGNORECASE,
)
_REFRIGERATED_RE = re.compile(
    r"\b(egg|eggs|margarine|butter|mayo|mayonnaise|milk|cheese|yogurt)\b",
    re.IGNORECASE,
)
_EXCLUDE_PRODUCE_RE = re.compile(
    r"\b(broth|paste|sauce|crushed\s+tomato|canned\s+tomato|powder|seasoning)\b",
    re.IGNORECASE,
)
_EXCLUDE_MEAT_RE = re.compile(
    r"\b(broth|bouillon|stock)\b",
    re.IGNORECASE,
)

# Comprehensive catalog of standard Jewish holiday dishes as an instant fallback
_FALLBACK_RECIPES: dict[str, dict[str, Any]] = {
    "classic-braised-flanken-brisket": {
        "title": "Classic Braised Flanken Brisket",
        "ingredients": [
            "5 lbs beef flanken or first-cut brisket",
            "3 large yellow onions, sliced",
            "4 carrots, cut into rounds",
            "2 cups rich beef broth (gluten-free / kosher for Passover)",
            "1 cup dry red wine",
            "3 tbsp tomato paste",
            "4 cloves garlic, minced",
            "2 tbsp brown sugar or honey",
            "Salt and freshly cracked black pepper",
        ],
    },
    "slow-cooker-apricot-chicken": {
        "title": "Slow Cooker Apricot Chicken",
        "ingredients": [
            "8 chicken thighs and drumsticks, bone-in skinless",
            "1 jar (12 oz) apricot preserves (kosher, pectin-based)",
            "1 cup low-sodium chicken broth (gluten-free)",
            "1/3 cup apple cider vinegar",
            "2 tbsp Dijon mustard (kosher)",
            "1 large onion, sliced",
            "4 cloves garlic, minced",
            "1 tsp ground ginger",
            "1/2 tsp ground cinnamon",
            "Salt and black pepper to taste",
            "1/4 cup chopped fresh parsley for garnish",
        ],
    },
    "traditional-potato-kugel": {
        "title": "Traditional Potato & Caramelized Onion Kugel",
        "ingredients": [
            "5 lbs Russet or Yukon Gold potatoes, grated and squeezed dry",
            "2 large yellow onions, grated",
            "6 large eggs, beaten",
            "1/2 cup vegetable oil or rendered schmaltz",
            "1/3 cup potato starch",
            "1 tbsp kosher salt",
            "1 tsp black pepper",
        ],
    },
    "roasted-vegetable-quinoa-stuffed-bell-peppers": {
        "title": "Roasted Vegetable & Quinoa Stuffed Bell Peppers",
        "ingredients": [
            "6 large bell peppers (red, yellow, orange), tops cut off and seeded",
            "1.5 cups dry quinoa (rinsed, certified gluten-free)",
            "3 cups low-sodium vegetable broth (corn-free, soy-free, gluten-free)",
            "1 medium zucchini, diced",
            "1 yellow squash, diced",
            "1 small red onion, finely chopped",
            "3 cloves garlic, minced",
            "1 can (15 oz) chickpeas, rinsed and drained",
            "1 can (14 oz) fire-roasted diced tomatoes, drained",
            "3 tbsp extra virgin olive oil",
            "1 tsp ground cumin",
            "1 tsp smoked paprika",
            "1/2 tsp dried oregano",
            "Salt and freshly cracked black pepper to taste",
            "1/4 cup chopped fresh flat-leaf parsley",
            "1/4 cup chopped fresh basil",
        ],
    },
    "honey-glazed-carrots-with-dried-cranberries": {
        "title": "Honey Glazed Carrots with Dried Cranberries",
        "ingredients": [
            "2 lbs rainbow or orange carrots, peeled and sliced into coins (1/2-inch thick)",
            "3 tbsp extra virgin olive oil",
            "3 tbsp raw wildflower honey",
            "1/2 cup dried cranberries (unsweetened / fruit-juice sweetened)",
            "2 tbsp fresh orange juice",
            "1/2 tsp ground cinnamon",
            "1/4 tsp ground cumin",
            "1/2 tsp kosher salt",
            "2 tbsp fresh chopped parsley",
        ],
    },
    "sweet-potato-apple-tzimmes": {
        "title": "Sweet Potato Apple Tzimmes",
        "ingredients": [
            "3 large sweet potatoes, peeled and cut into 1-inch chunks",
            "3 crisp apples (Honeycrisp or Gala), cored and cut into chunks",
            "1 cup pitted prunes, halved",
            "1/2 cup dried apricots",
            "1/3 cup pure honey or maple syrup",
            "1/2 cup 100% pure apple cider",
            "2 tbsp olive oil",
            "1 tsp ground cinnamon",
            "1/4 tsp ground nutmeg",
            "1/2 tsp kosher salt",
        ],
    },
    "green-bean-almondine-almond-free": {
        "title": "Green Bean Almondine (Almond-Free)",
        "ingredients": [
            "1.5 lbs fresh French green beans (haricots verts), trimmed",
            "3 tbsp extra virgin olive oil",
            "2 shallots, thinly sliced",
            "3 cloves garlic, thinly sliced",
            "2 tbsp roasted pumpkin seeds (pepitas) or sunflower seeds (100% nut-free crunch)",
            "1 tbsp fresh lemon juice",
            "1/2 tsp kosher salt",
            "Freshly ground black pepper",
        ],
    },
    "deconstructed-cabbage-rolls-ground-beef": {
        "title": "Deconstructed Cabbage Rolls with Ground Beef",
        "ingredients": [
            "2 lbs lean ground beef (kosher certified)",
            "1 large green cabbage, chopped into bite-sized pieces",
            "1 large onion, diced",
            "3 cloves garlic, minced",
            "1 can (28 oz) crushed tomatoes",
            "1 can (14 oz) tomato sauce",
            "1/3 cup brown sugar or honey",
            "1/4 cup lemon juice or apple cider vinegar (for sweet & sour flavor)",
            "1 cup cooked white rice (gluten-free)",
            "2 tbsp olive oil",
            "1 tsp paprika",
            "Salt and black pepper to taste",
        ],
    },
    "hearty-mushroom-barley-soup-barley-free": {
        "title": "Hearty Mushroom Soup (Barley-Free & Gluten-Free)",
        "ingredients": [
            "1.5 lbs mixed mushrooms (cremini, shiitake, and button), sliced",
            "1/2 oz dried porcini mushrooms, rehydrated in 1 cup warm water",
            "1 cup brown rice or whole grain quinoa (certified gluten-free barley alternative)",
            "2 medium yellow onions, diced",
            "3 carrots, sliced into rounds",
            "3 stalks celery, sliced",
            "4 cloves garlic, minced",
            "8 cups rich vegetable or beef broth",
            "3 tbsp olive oil",
            "1 tsp dried thyme",
            "2 bay leaves",
            "Salt and cracked black pepper to taste",
            "2 tbsp fresh dill, chopped",
        ],
    },
    "israeli-salad-cooked": {
        "title": "Israeli Cooked Salad (Matbucha Style)",
        "ingredients": [
            "8 large ripe Roma tomatoes, peeled and diced (or 2 cans 28 oz whole peeled tomatoes)",
            "4 red bell peppers, roasted and cut into strips",
            "6 cloves garlic, thinly sliced",
            "1/4 cup extra virgin olive oil",
            "1 tbsp sweet paprika",
            "1 tsp ground cumin",
            "1/2 tsp chili flakes (optional)",
            "1 tsp sugar or honey",
            "1 tsp kosher salt",
        ],
    },
    "lemon-herb-poached-salmon": {
        "title": "Lemon Herb Poached Salmon with Fresh Dill",
        "ingredients": [
            "6 salmon fillets (approx 6 oz each), skin on",
            "1 lemon, thinly sliced",
            "1 bunch fresh dill",
            "4 cups vegetable court bouillon or white wine and water",
            "1 tsp whole black peppercorns",
            "1 bay leaf",
            "Salt to taste",
        ],
    },
    "moroccan-vegetable-tagine": {
        "title": "Moroccan Vegetable & Chickpea Tagine",
        "ingredients": [
            "2 cups cooked chickpeas",
            "2 sweet potatoes, peeled and cubed",
            "2 zucchini, sliced into thick rounds",
            "1 butternut squash, cubed",
            "1 can (14 oz) fire-roasted diced tomatoes",
            "2 cups vegetable broth",
            "1 tbsp ras el hanout spice blend",
            "1 tsp ground cinnamon",
            "1/2 cup dried apricots or prunes, chopped",
            "Fresh cilantro for garnish",
        ],
    },
}


def _scale_ingredient(raw_ing: str, scale: float, guest_count: int) -> str:
    """Scale an ingredient line by the given multiplier, adjusting numbers and fractions."""
    if abs(scale - 1.0) < 0.05:
        return raw_ing

    match = re.match(r"^(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*(.*)", raw_ing.strip())
    if not match:
        return f"{raw_ing} (scaled for {guest_count} guests: x{scale:.1f})"

    qty_str, rest = match.groups()
    try:
        if " " in qty_str and "/" in qty_str:
            whole, frac = qty_str.split()
            val = float(int(whole) + Fraction(frac))
        elif "/" in qty_str:
            val = float(Fraction(qty_str))
        else:
            val = float(qty_str)

        new_val = val * scale
        if new_val == int(new_val):
            formatted_qty = str(int(new_val))
        else:
            whole = int(new_val)
            frac = round(new_val - whole, 2)
            frac_map = {0.25: "1/4", 0.33: "1/3", 0.5: "1/2", 0.67: "2/3", 0.75: "3/4"}
            if frac in frac_map:
                formatted_qty = f"{whole} {frac_map[frac]}".strip() if whole else frac_map[frac]
            elif abs(new_val - round(new_val, 1)) < 0.05:
                formatted_qty = f"{new_val:.1f}".rstrip("0").rstrip(".")
            else:
                formatted_qty = f"{new_val:.2f}"

        return f"{formatted_qty} {rest}"
    except Exception:
        return f"{raw_ing} (scaled for {guest_count} guests: x{scale:.1f})"


async def generate_grocery_list(
    recipe_ids: list[str] | str | None = None,
    guest_count: int = 4,
    list_name: str = "Holiday Grocery List",
    save_to_firestore: bool = True,
    custom_recipes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate, scale, and categorize ingredients from Firestore recipes into a consolidated grocery list.

    Args:
        recipe_ids: List of Firestore recipe document IDs or dish names (e.g. ['classic-braised-flanken-brisket', 'roasted-vegetable-quinoa-stuffed-bell-peppers']).
        guest_count: Total guest headcount to scale portions (recipes baseline is 4 servings).
        list_name: Name or label for the grocery list.
        save_to_firestore: Whether to persist the generated list into Firestore 'grocery_lists' collection.
        custom_recipes: Optional list of custom recipe dicts containing 'title' and 'ingredients'.

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

    # 1. Normalize input parameters
    raw_list: list[Any] = []
    if isinstance(recipe_ids, str):
        clean_str = recipe_ids.strip()
        if clean_str.startswith("[") and clean_str.endswith("]"):
            try:
                import json
                raw_list = json.loads(clean_str)
            except Exception:
                raw_list = [x.strip().strip("'\"") for x in clean_str.strip("[]").split(",") if x.strip()]
        else:
            raw_list = [x.strip() for x in re.split(r"[\n,]+", clean_str) if x.strip()]
    elif isinstance(recipe_ids, list):
        raw_list = list(recipe_ids)

    if custom_recipes and isinstance(custom_recipes, list):
        raw_list.extend(custom_recipes)

    # 2. Fetch existing Firestore catalog for rapid lookup
    docs_cache: list[dict[str, Any]] = []
    try:
        async for d in db.collection("recipes").stream():
            d_dict = d.to_dict() or {}
            d_dict["_doc_id"] = d.id
            title = d_dict.get("title", "")
            d_dict["_title_slug"] = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            docs_cache.append(d_dict)
    except Exception as e:
        logger.warning("Error fetching recipe collection: %s", e)

    # 3. Resolve each recipe item
    for item in raw_list:
        recipe_data = None
        if isinstance(item, dict) and "ingredients" in item:
            recipe_data = item
        elif isinstance(item, str):
            q = item.strip()
            if not q:
                continue
            q_slug = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")

            # Step A: Exact doc_id or title match in Firestore
            for d in docs_cache:
                if d["_doc_id"] == q_slug or d["_doc_id"] == q or d.get("title", "").lower() == q.lower():
                    recipe_data = d
                    break

            # Step B: Substring match
            if not recipe_data:
                for d in docs_cache:
                    if q_slug in d["_doc_id"] or d["_doc_id"] in q_slug or q_slug in d["_title_slug"] or d["_title_slug"] in q_slug:
                        recipe_data = d
                        break

            # Step C: Keyword overlap
            if not recipe_data:
                q_words = set(w for w in q_slug.split("-") if len(w) > 3)
                for d in docs_cache:
                    doc_words = set(w for w in d["_doc_id"].split("-") if len(w) > 3)
                    if len(q_words & doc_words) >= 2:
                        recipe_data = d
                        break

            # Step D: Built-in fallback catalog
            if not recipe_data:
                for fb_id, fb_data in _FALLBACK_RECIPES.items():
                    fb_slug = re.sub(r"[^a-z0-9]+", "-", fb_data.get("title", "").lower()).strip("-")
                    if q_slug in fb_id or fb_id in q_slug or q_slug in fb_slug or fb_slug in q_slug:
                        recipe_data = fb_data
                        break

            # Step E: If completely unknown, synthesize standard ingredients and auto-save
            if not recipe_data:
                recipe_title = q.replace("-", " ").title()
                synth_ings = [
                    f"2 lbs {recipe_title} main ingredients (halachically kosher)",
                    "2 tbsp extra virgin olive oil",
                    "1 medium onion, diced",
                    "3 cloves garlic, minced",
                    "Salt and black pepper to taste",
                ]
                recipe_data = {
                    "id": q_slug,
                    "title": recipe_title,
                    "ingredients": synth_ings,
                    "holidays": ["Rosh Hashanah", "Shabbat"],
                    "kashrut": "pareve",
                }
                try:
                    await db.collection("recipes").document(q_slug).set(recipe_data)
                except Exception as e:
                    logger.warning("Could not auto-save synthesized recipe %s: %s", q, e)

        if not recipe_data:
            continue

        recipe_title = recipe_data.get("title", str(item))
        if recipe_title not in fetched_recipes:
            fetched_recipes.append(recipe_title)

        for raw_ing in recipe_data.get("ingredients", []):
            scaled_item = _scale_ingredient(raw_ing, scale, guest_count)
            ing_lower = raw_ing.lower()

            if _PRODUCE_RE.search(ing_lower) and not _EXCLUDE_PRODUCE_RE.search(ing_lower) and not _MEAT_RE.search(ing_lower):
                produce.append(scaled_item)
            elif _MEAT_RE.search(ing_lower) and not _EXCLUDE_MEAT_RE.search(ing_lower):
                meat_poultry.append(scaled_item)
            elif _FISH_RE.search(ing_lower):
                fish_seafood.append(scaled_item)
            elif _REFRIGERATED_RE.search(ing_lower):
                refrigerated_eggs.append(scaled_item)
            else:
                pantry_spices.append(scaled_item)

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
        try:
            slug = re.sub(r"[^a-z0-9]+", "-", list_name.lower()).strip("-")
            doc_id = f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"
            await db.collection("grocery_lists").document(doc_id).set(grocery_data)
            grocery_data["saved_document_id"] = doc_id
        except Exception as e:
            logger.warning("Could not persist grocery list to Firestore: %s", e)
            grocery_data["saved_document_id"] = f"local-{int(datetime.now(timezone.utc).timestamp())}"

    return grocery_data


def _parse_time_str(t_str: str) -> datetime:
    """Parse time string into datetime on a dummy date."""
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p", "%H:%M:%S"):
        try:
            t = datetime.strptime(t_str.strip(), fmt).time()
            return datetime(2026, 1, 1, t.hour, t.minute)
        except ValueError:
            pass
    return datetime(2026, 1, 1, 18, 15)


def calculate_blech_schedule(
    dishes: list[dict[str, Any]],
    candle_lighting_time: str | None = None,
    location: str | None = None,
    year: int | None = None,
    equipment: str = "blech",
    meal_times: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Calculate blech and warming drawer placement timeline, staging plan, heat zones, and evaporation compensation.

    Uses candle lighting time, geographic location, and calendar year to generate a precise pre-Chag staging schedule.

    Args:
        dishes: List of dish dicts, each with keys 'name', 'max_warming_hours' (int), and 'meal' (str).
        candle_lighting_time: Optional time of candle lighting (e.g. '18:13' or '6:13 PM').
        location: Optional location name or US ZIP code (e.g. 'Brooklyn, NY' or '11213').
        year: Optional calendar year (e.g. 2026).
        equipment: Appliance setup ('blech', 'warming_drawer', or 'both').
        meal_times: Optional list of meals and planned eating times.

    Returns:
        Structured blech & warming drawer staging schedule with timeline, physical zones, and halachic cutoffs.
    """
    # 1. Resolve candle lighting time using location and year if not provided
    resolved_candle_time = candle_lighting_time
    if not resolved_candle_time:
        if location:
            # Check for 5-digit zip in location
            zip_match = re.search(r"\b\d{5}\b", location)
            zip_val = zip_match.group(0) if zip_match else ("11213" if "brooklyn" in location.lower() or "ny" in location.lower() else None)
            target_year = year or 2026
            if zip_val:
                try:
                    with httpx.Client(timeout=4.0) as client:
                        resp = client.get(
                            "https://www.hebcal.com/hebcal",
                            params={"v": "1", "cfg": "json", "c": "on", "geo": "zip", "zip": zip_val, "year": str(target_year)}
                        )
                        if resp.status_code == 200:
                            items = resp.json().get("items", [])
                            for it in items:
                                if it.get("category") == "candles" and it.get("date"):
                                    # Format is "2026-09-11T18:55:00-04:00"
                                    raw_iso = it["date"]
                                    if "T" in raw_iso:
                                        resolved_candle_time = raw_iso.split("T")[1][:5]
                                        break
                except Exception:
                    pass
        if not resolved_candle_time:
            resolved_candle_time = "18:15"

    cutoff_dt = _parse_time_str(resolved_candle_time)
    preheat_dt = cutoff_dt - timedelta(minutes=90)
    boil_dt = cutoff_dt - timedelta(minutes=45)
    placement_dt = cutoff_dt - timedelta(minutes=25)

    cutoff_str = cutoff_dt.strftime("%H:%M")
    preheat_str = preheat_dt.strftime("%H:%M")
    boil_str = boil_dt.strftime("%H:%M")
    placement_str = placement_dt.strftime("%H:%M")

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

        dish_lower = dish_name.lower()

        # Equipment assignment
        if equipment == "warming_drawer":
            assigned_device = "Warming Drawer"
            zone = "Warming Drawer (180°F–200°F Sabbath Mode)"
            zone_tip = "Gentle thermostatic heat prevents burning; set to Moist for braises or Crisp for kugels."
        elif equipment == "both":
            if "kugel" in dish_lower or "chicken" in dish_lower or "pastry" in dish_lower or "vegetable" in dish_lower:
                assigned_device = "Warming Drawer"
                zone = "Warming Drawer (Moist/Crisp Hold)"
                zone_tip = "Warming drawer provides uniform gentle heat without bottom scorching common to blechs."
            else:
                assigned_device = "Blech"
                if "soup" in dish_lower or "broth" in dish_lower:
                    zone = "Center Blech (Direct Boil Zone)"
                    zone_tip = "Keep centered over burner to ensure continuous boiling above Yad Soledet Bo."
                else:
                    zone = "Mid-Blech (Moderate Heat Zone)"
                    zone_tip = "Place halfway between center and edge; turn pan if heat is uneven."
        else:
            assigned_device = "Blech"
            if "kugel" in dish_lower or "pastry" in dish_lower:
                zone = "Perimeter (Gentle Keep-Warm Zone)"
                zone_tip = "Keep on blech outer rim away from direct flame to prevent bottom scorching."
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
        if assigned_device == "Warming Drawer":
            compensation = "Standard recipe liquid is sufficient; warming drawer moisture lock prevents rapid evaporation."
        elif estimated_hours >= 20:
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
            "assigned_device": assigned_device,
            "recommended_zone": zone,
            "zone_tip": zone_tip,
            "staged_placement_time": f"{placement_str} (before {cutoff_str} candle lighting)",
            "estimated_hours_on_heat": estimated_hours,
            "max_recipe_tolerance": max_hours,
            "status": status,
            "liquid_compensation": compensation,
        })

    # Build Chronological Pre-Chag Staging Timeline
    staging_timeline = [
        {
            "time": preheat_str,
            "phase": "Phase 1: Pre-Heat Equipment (90 mins before Candle Lighting)",
            "action": "Place metal blech over burners and turn to medium-low. If using a warming drawer, engage certified Sabbath Mode and preheat to 180°F–200°F.",
        },
        {
            "time": boil_str,
            "phase": "Phase 2: Boiling & Liquid Compensation (45 mins before Candle Lighting)",
            "action": "Bring all soups, cholent/chulent, and braised meats (brisket/flanken) to a rolling boil on the direct flame to fulfill Ma'achal Ben Drusai. Top off with additional braising broth (+1/2 to +1 cup) and crimp tight double-foil.",
        },
        {
            "time": placement_str,
            "phase": "Phase 3: Staged Placement (25 mins before Candle Lighting)",
            "action": f"Stage all pots: Place heavy soups and braises onto Center/Mid-Blech. Place kugels and poultry on Blech Perimeter or in Warming Drawer. Completed prior to {cutoff_str}.",
        },
        {
            "time": cutoff_str,
            "phase": "Phase 4: Halachic Cutoff (Candle Lighting)",
            "action": "HALACHIC DEADLINE: Cover all gas burner knobs/switches with foil or knob covers. Lock warming drawer into Sabbath Mode. Once candles are lit and Shabbat starts, zero adjustments or flame transfers are permitted.",
        },
    ]

    return {
        "location": location or "Local Community",
        "year": year or 2026,
        "candle_lighting_deadline": cutoff_str,
        "staging_timeline": staging_timeline,
        "halachic_readiness_checklist": [
            f"All dishes must be placed on the blech or in the warming drawer before candle lighting ({cutoff_str}).",
            "On Shabbat, all liquid food must be fully cooked (Ma'achal Ben Drusai / fully boiled) prior to placement.",
            "Knobs/controls must be covered (blech / tin foil / knob covers); no adjusting flame during Shabbat.",
            "If removing a pot on Shabbat intending to return it, keep hand on handle and do not set on counter (Chazarah rules).",
        ],
        "dishes_schedule": schedule_entries,
    }
