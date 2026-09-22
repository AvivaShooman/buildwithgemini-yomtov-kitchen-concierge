#!/usr/bin/env python3
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

"""Seed script to populate Firestore 'recipes' collection with canonical holiday recipes.

CRITICAL REQUIREMENT:
The GCP Project ID is hardcoded as a string constant to prevent Agent Platform
from resolving the numeric project number (821049907373).
"""

import datetime
from google.cloud import firestore

# Hardcoded project ID as required per platform constraints
PROJECT_ID = "qwiklabs-gcp-04-ded35b1abcfb"
COLLECTION_NAME = "recipes"

SEED_RECIPES = [
    {
        "id": "classic-braised-flanken-brisket",
        "title": "Classic Braised Flanken Brisket",
        "holidays": ["Rosh Hashanah", "Pesach", "Sukkot", "Shabbat"],
        "course": "main",
        "kashrut": "meat",
        "blech_friendly": True,
        "warming_drawer_friendly": True,
        "max_warming_hours": 24,
        "evaporation_compensation": "Add +1/2 cup beef broth and seal with double foil before placing on the blech",
        "day2_leftover_quality": "Outstanding - brisket tenderizes further in braising jus overnight",
        "allergens": [],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "celiac-safe", "passover-friendly"],
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
        "instructions": (
            "1. Brown brisket in dutch oven on both sides. Remove and sauté onions and garlic until caramelized.\n"
            "2. Stir in tomato paste, red wine, and broth, scraping up browned bits.\n"
            "3. Return meat, cover tightly, and braise at 325°F for 3.5 hours until fork-tender.\n"
            "4. Slice across the grain cold, return to sauce.\n"
            "5. Yom Tov warming: keep completely covered in sauce with double foil on perimeter of blech."
        ),
        "ratings": {
            "crowd_rating": 4.9,
            "ease_of_prep": 4.2,
            "yomtov_suitability": 5.0,
            "review_count": 12,
        },
        "feedback_history": [
            {
                "crowd_rating": 5,
                "ease_of_prep": 4,
                "yomtov_suitability": 5,
                "notes": "Held up for 22 hours on the blech across Rosh Hashanah Day 1 & Day 2. Meat melted in mouth.",
                "timestamp": "2026-09-15T18:00:00Z",
            }
        ],
        "notes": "Ideal holiday centerpiece. Fully cooked Erev Yom Tov. Halachic note: liquid must be fully cooked prior to Shabbat.",
    },
    {
        "id": "honey-pomegranate-roasted-chicken",
        "title": "Honey Pomegranate Roasted Chicken",
        "holidays": ["Rosh Hashanah", "Sukkot", "Shavuot", "Shabbat"],
        "course": "main",
        "kashrut": "meat",
        "blech_friendly": True,
        "warming_drawer_friendly": True,
        "max_warming_hours": 18,
        "evaporation_compensation": "Baste generously with 1/3 cup reserved pomegranate honey glaze before warming",
        "day2_leftover_quality": "Good - retain cover to prevent breast meat from drying out",
        "allergens": [],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "celiac-safe"],
        "ingredients": [
            "2 whole chickens, cut into eighths",
            "1/2 cup pomegranate molasses",
            "1/3 cup raw honey",
            "1/4 cup olive oil",
            "1 tbsp fresh rosemary, chopped",
            "1 tbsp fresh thyme",
            "2 tsp paprika",
            "Salt and black pepper to taste",
        ],
        "instructions": (
            "1. Whisk pomegranate molasses, honey, olive oil, herbs, paprika, salt, and pepper into a glaze.\n"
            "2. Marinate chicken pieces for at least 2 hours.\n"
            "3. Roast at 400°F for 45-50 minutes until golden brown and internal temp reaches 165°F.\n"
            "4. Baste with pan juices.\n"
            "5. To hold on blech: place in deep 9x13 pan, add 1/4 cup broth, cover tightly with foil."
        ),
        "ratings": {
            "crowd_rating": 4.8,
            "ease_of_prep": 4.6,
            "yomtov_suitability": 4.7,
            "review_count": 8,
        },
        "feedback_history": [
            {
                "crowd_rating": 5,
                "ease_of_prep": 5,
                "yomtov_suitability": 4,
                "notes": "Delicious sweet and tangy Rosh Hashanah flavor. Covered tightly it stayed juicy.",
                "timestamp": "2026-09-18T12:00:00Z",
            }
        ],
        "notes": "Festive Simanim dish for Rosh Hashanah. Reheats easily for Yom Tov lunch.",
    },
    {
        "id": "traditional-potato-kugel",
        "title": "Traditional Potato & Caramelized Onion Kugel",
        "holidays": ["Rosh Hashanah", "Pesach", "Sukkot", "Shavuot", "Shabbat"],
        "course": "side",
        "kashrut": "pareve",
        "blech_friendly": True,
        "warming_drawer_friendly": True,
        "max_warming_hours": 20,
        "evaporation_compensation": "Place parchment paper directly under foil; warm on low perimeter zone of blech",
        "day2_leftover_quality": "Very Good - crust stays crisp if foil is vented slightly during final 30 min",
        "allergens": ["eggs"],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "celiac-safe", "passover-friendly"],
        "ingredients": [
            "5 lbs Russet or Yukon Gold potatoes, grated and squeezed dry",
            "2 large yellow onions, grated",
            "6 large eggs, beaten",
            "1/2 cup vegetable oil or rendered schmaltz",
            "1/3 cup potato starch",
            "1 tbsp kosher salt",
            "1 tsp black pepper",
        ],
        "instructions": (
            "1. Preheat oven to 400°F with oil in a 9x13 metal baking dish for 10 minutes.\n"
            "2. Combine grated potatoes, onions, beaten eggs, potato starch, salt, and pepper.\n"
            "3. Carefully pour mixture into the hot oiled pan (it should sizzle immediately to create a crisp crust).\n"
            "4. Bake for 75-90 minutes until deeply golden and crispy on top.\n"
            "5. Blech warming: keep on perimeter zone. Safe for overnight warming."
        ),
        "ratings": {
            "crowd_rating": 4.9,
            "ease_of_prep": 3.8,
            "yomtov_suitability": 4.8,
            "review_count": 15,
        },
        "feedback_history": [
            {
                "crowd_rating": 5,
                "ease_of_prep": 4,
                "yomtov_suitability": 5,
                "notes": "Survived 18h overnight warming with crispy edges and creamy center. Fully celiac safe.",
                "timestamp": "2026-09-16T20:00:00Z",
            }
        ],
        "notes": "Classic Ashkenazi Shabbat and Yom Tov staple. Naturally gluten-free when made with potato starch.",
    },
    {
        "id": "lemon-herb-poached-salmon",
        "title": "Lemon Herb Poached Salmon with Fresh Dill",
        "holidays": ["Rosh Hashanah", "Pesach", "Shavuot", "Sukkot", "Shabbat"],
        "course": "fish",
        "kashrut": "pareve",
        "blech_friendly": False,
        "warming_drawer_friendly": True,
        "max_warming_hours": 4,
        "evaporation_compensation": "Submerge halfway in poaching broth; do NOT put on direct blech heat or fish will dry out",
        "day2_leftover_quality": "Best served chilled or room temperature for Day 2 Yom Tov lunch",
        "allergens": ["fish"],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "celiac-safe", "low-carb"],
        "ingredients": [
            "6 salmon fillets (approx 6 oz each), skin on",
            "1 lemon, thinly sliced",
            "1 bunch fresh dill",
            "4 cups vegetable court bouillon or white wine and water",
            "1 tsp whole black peppercorns",
            "1 bay leaf",
            "Salt to taste",
        ],
        "instructions": (
            "1. Bring court bouillon, lemon slices, dill, peppercorns, and bay leaf to a gentle simmer.\n"
            "2. Gently lower salmon fillets into liquid. Simmer on low heat for 8-10 minutes until opaque.\n"
            "3. Carefully remove and cool in poaching liquid to retain maximum moisture.\n"
            "4. Serve chilled with dill sauce or warm gently in covered dish with liquid in warming drawer."
        ),
        "ratings": {
            "crowd_rating": 4.7,
            "ease_of_prep": 4.8,
            "yomtov_suitability": 3.2,
            "review_count": 6,
        },
        "feedback_history": [
            {
                "crowd_rating": 5,
                "ease_of_prep": 5,
                "yomtov_suitability": 3,
                "notes": "Outstanding when eaten fresh or chilled for Day 2 lunch. Dries out quickly if left on direct blech heat.",
                "timestamp": "2026-09-17T14:00:00Z",
            }
        ],
        "notes": "Ideal starter for holiday meals. Perfect chilled for multi-day Yom Tov lunches when hot food is inconvenient.",
    },
    {
        "id": "moroccan-vegetable-tagine",
        "title": "Moroccan Vegetable & Chickpea Tagine",
        "holidays": ["Sukkot", "Chol HaMoed", "Shavuot"],
        "course": "main",
        "kashrut": "pareve",
        "blech_friendly": True,
        "warming_drawer_friendly": True,
        "max_warming_hours": 16,
        "evaporation_compensation": "Add 1/2 cup vegetable broth or crushed tomatoes before placing on blech",
        "day2_leftover_quality": "Superb - aromatic North African spices bloom and deepen overnight",
        "allergens": [],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "vegan", "celiac-safe"],
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
        "instructions": (
            "1. Sauté onions, garlic, and ras el hanout in olive oil until fragrant.\n"
            "2. Add sweet potatoes, squash, zucchini, chickpeas, diced tomatoes, broth, and dried fruit.\n"
            "3. Bring to a boil, then reduce heat and simmer covered for 40 minutes until vegetables are tender.\n"
            "4. Yom Tov blech holding: keep in heavy covered pot; sauce prevents any burning or drying."
        ),
        "ratings": {
            "crowd_rating": 4.6,
            "ease_of_prep": 4.5,
            "yomtov_suitability": 4.9,
            "review_count": 5,
        },
        "feedback_history": [
            {
                "crowd_rating": 5,
                "ease_of_prep": 4,
                "yomtov_suitability": 5,
                "notes": "Served in the Sukkah on Sukkot Day 1. Stew held warmth wonderfully and tasted even better on Chol HaMoed.",
                "timestamp": "2026-09-19T19:30:00Z",
            }
        ],
        "notes": "Comforting stew perfect for chilly Sukkah nights. Note: contains chickpeas (kitniyot), great for Sephardic custom and Sukkot/Chol HaMoed.",
    },
]


def seed_database():
    """Populates Firestore recipes collection with canonical seed items."""
    print(f"Connecting to Firestore with hardcoded Project ID: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    recipes_col = db.collection(COLLECTION_NAME)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for item in SEED_RECIPES:
        doc_id = item["id"]
        payload = {k: v for k, v in item.items() if k != "id"}
        payload["created_at"] = now_iso
        recipes_col.document(doc_id).set(payload)
        print(f"  ✓ Seeded recipe: {item['title']} (ID: {doc_id})")

    print(f"Successfully seeded {len(SEED_RECIPES)} recipes into Firestore collection '{COLLECTION_NAME}'!")


if __name__ == "__main__":
    seed_database()
