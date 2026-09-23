#!/usr/bin/env python3
# Copyright 2026 Google LLC
"""Seeds the user's complete Rosh Hashanah & Shabbat menu recipes into Firestore."""

import asyncio
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-ded35b1abcfb"

MENU_RECIPES = [
    {
        "id": "slow-cooker-apricot-chicken",
        "title": "Slow Cooker Apricot Chicken",
        "holidays": ["Rosh Hashanah", "Sukkot", "Shabbat"],
        "course": "main",
        "kashrut": "meat",
        "blech_friendly": True,
        "warming_drawer_friendly": True,
        "max_warming_hours": 18,
        "evaporation_compensation": "Reserve 1/2 cup apricot braising sauce and pour over before warming on the blech",
        "day2_leftover_quality": "Outstanding - slow cooked chicken stays juicy and tender in rich apricot glaze",
        "allergens": [],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "corn-free", "soy-free"],
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
        "instructions": (
            "1. Place sliced onions and minced garlic at the bottom of the slow cooker or Dutch oven.\n"
            "2. Season chicken pieces with salt, pepper, ginger, and cinnamon; arrange over onions.\n"
            "3. Whisk together apricot preserves, chicken broth, apple cider vinegar, and Dijon mustard; pour evenly over chicken.\n"
            "4. Cook on LOW for 6-7 hours or bake covered at 325°F for 2.5 hours until fork tender.\n"
            "5. To hold on blech: keep sealed tightly in sauce on perimeter zone."
        ),
        "notes": "Classic Rosh Hashanah main dish featuring sweet simanim (apricots and apples).",
    },
    {
        "id": "honey-glazed-carrots-with-dried-cranberries",
        "title": "Honey Glazed Carrots with Dried Cranberries",
        "holidays": ["Rosh Hashanah", "Sukkot", "Shabbat"],
        "course": "side",
        "kashrut": "pareve",
        "blech_friendly": True,
        "warming_drawer_friendly": True,
        "max_warming_hours": 16,
        "evaporation_compensation": "Toss with 2 tbsp orange juice and 1 tbsp olive oil before blech warming",
        "day2_leftover_quality": "Excellent - carrots remain tender and glaze intensifies",
        "allergens": [],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "corn-free", "soy-free", "vegan"],
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
        "instructions": (
            "1. In a large skillet or roasting pan, heat olive oil over medium-high heat.\n"
            "2. Add sliced carrots, salt, cinnamon, and cumin; sauté for 5 minutes.\n"
            "3. Stir in orange juice and honey, reduce heat to low, cover, and braise for 15-20 minutes until tender.\n"
            "4. Fold in dried cranberries and chopped parsley during the final 3 minutes.\n"
            "5. To hold on blech: place in covered tin on perimeter warming zone."
        ),
        "notes": "Traditional Meren (carrots) for Rosh Hashanah signifying increased blessings.",
    },
    {
        "id": "sweet-potato-apple-tzimmes",
        "title": "Sweet Potato Apple Tzimmes",
        "holidays": ["Rosh Hashanah", "Sukkot", "Shabbat"],
        "course": "side",
        "kashrut": "pareve",
        "blech_friendly": True,
        "warming_drawer_friendly": True,
        "max_warming_hours": 20,
        "evaporation_compensation": "Add 1/3 cup apple cider and crimp foil tightly before blech holding",
        "day2_leftover_quality": "Superb - sweet potatoes and apples caramelize further without drying out",
        "allergens": [],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "corn-free", "soy-free", "vegan"],
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
        "instructions": (
            "1. Preheat oven to 350°F.\n"
            "2. Combine sweet potatoes, apples, prunes, and apricots in a 9x13 baking dish.\n"
            "3. Whisk honey, apple cider, olive oil, cinnamon, nutmeg, and salt; pour over produce.\n"
            "4. Cover tightly with heavy-duty foil and bake for 60 minutes.\n"
            "5. Uncover and bake 15 minutes more until syrupy and caramelized.\n"
            "6. Safe for overnight blech or warming drawer holding."
        ),
        "notes": "Traditional Ashkenazi Rosh Hashanah sweet stew.",
    },
    {
        "id": "green-bean-almondine-almond-free",
        "title": "Green Bean Almondine (Almond-Free)",
        "holidays": ["Rosh Hashanah", "Sukkot", "Shabbat"],
        "course": "side",
        "kashrut": "pareve",
        "blech_friendly": True,
        "warming_drawer_friendly": True,
        "max_warming_hours": 12,
        "evaporation_compensation": "Toss with 1 tbsp olive oil and keep in double-foiled container on low zone",
        "day2_leftover_quality": "Good - beans stay flavorful with roasted garlic and shallots",
        "allergens": [],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "corn-free", "soy-free", "allergen-friendly"],
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
        "instructions": (
            "1. Blanch trimmed green beans in salted boiling water for 3 minutes, then shock in ice bath and drain.\n"
            "2. Heat olive oil in a skillet over medium heat; sauté shallots and garlic until fragrant and golden.\n"
            "3. Add green beans, pepitas, and lemon juice; toss for 2-3 minutes until heated through.\n"
            "4. Season with salt and pepper.\n"
            "5. Keep in warming drawer or perimeter of blech."
        ),
        "notes": "100% tree nut free and sesame free variation of classic Almondine.",
    },
    {
        "id": "deconstructed-cabbage-rolls-ground-beef",
        "title": "Deconstructed Cabbage Rolls with Ground Beef",
        "holidays": ["Sukkot", "Rosh Hashanah", "Shabbat"],
        "course": "main",
        "kashrut": "meat",
        "blech_friendly": True,
        "warming_drawer_friendly": True,
        "max_warming_hours": 24,
        "evaporation_compensation": "Add 1/2 cup tomato sauce or broth before placing on blech",
        "day2_leftover_quality": "Outstanding - flavors meld together into a rich sweet and sour stew",
        "allergens": [],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "corn-free", "soy-free"],
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
        "instructions": (
            "1. In a large Dutch oven, brown ground beef with onions and garlic in olive oil. Drain excess fat.\n"
            "2. Add crushed tomatoes, tomato sauce, brown sugar, lemon juice, paprika, salt, and pepper; bring to simmer.\n"
            "3. Add chopped cabbage in batches, stirring until wilted into the sauce.\n"
            "4. Fold in cooked rice, cover tightly, and simmer on low for 45 minutes.\n"
            "5. Excellent overnight blech holding dish; keeps hot and flavorful for 24 hours."
        ),
        "notes": "Traditional Sukkot stuffed cabbage flavors in an easy one-pot deconstructed braise.",
    },
    {
        "id": "hearty-mushroom-barley-soup-barley-free",
        "title": "Hearty Mushroom Soup (Barley-Free & Gluten-Free)",
        "holidays": ["Rosh Hashanah", "Sukkot", "Shabbat"],
        "course": "soup",
        "kashrut": "pareve",
        "blech_friendly": True,
        "warming_drawer_friendly": True,
        "max_warming_hours": 24,
        "evaporation_compensation": "Add 1 cup vegetable broth before placing on blech; holds beautifully on center zone",
        "day2_leftover_quality": "Superb - mushroom broth deepens and develops deep savory umami",
        "allergens": [],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "corn-free", "soy-free", "vegan"],
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
        "instructions": (
            "1. In a large soup pot, heat olive oil over medium-high heat. Sauté onions, carrots, and celery for 8 minutes.\n"
            "2. Add fresh and rehydrated mushrooms with minced garlic and thyme; cook until browned.\n"
            "3. Pour in broth, strained porcini soaking liquid, bay leaves, and rinsed brown rice/quinoa.\n"
            "4. Bring to a rolling boil, then lower heat, cover, and simmer for 45 minutes until grains are tender.\n"
            "5. Season with salt, pepper, and fresh dill.\n"
            "6. Yom Tov blech: place on center boil zone with tight lid."
        ),
        "notes": "Classic Ashkenazi holiday soup made 100% gluten-free and celiac safe.",
    },
    {
        "id": "israeli-salad-cooked",
        "title": "Israeli Cooked Salad (Matbucha Style)",
        "holidays": ["Rosh Hashanah", "Sukkot", "Shabbat"],
        "course": "salad",
        "kashrut": "pareve",
        "blech_friendly": True,
        "warming_drawer_friendly": True,
        "max_warming_hours": 24,
        "evaporation_compensation": "Drizzle with 1 tbsp olive oil before blech warming; can also be served chilled",
        "day2_leftover_quality": "Outstanding - slow cooked tomatoes and sweet peppers deepen in sweetness",
        "allergens": [],
        "dietary_tags": ["gluten-free", "nut-free", "sesame-free", "corn-free", "soy-free", "vegan"],
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
        "instructions": (
            "1. Heat olive oil in a heavy saucepan over medium-low heat. Add garlic and paprika, blooming for 1 minute.\n"
            "2. Add diced tomatoes, roasted bell peppers, cumin, salt, and sugar.\n"
            "3. Simmer uncovered on very low heat for 1.5 to 2 hours, stirring occasionally until thick, jammy, and oil separates.\n"
            "4. Can be served warm from the blech or chilled as a festive Shabbat dip."
        ),
        "notes": "Slow-cooked Moroccan and Sephardic Shabbat dip.",
    },
]

async def seed():
    db = firestore.AsyncClient(project=PROJECT_ID)
    print(f"Seeding {len(MENU_RECIPES)} recipes into Firestore collection 'recipes'...")
    for r in MENU_RECIPES:
        doc_ref = db.collection("recipes").document(r["id"])
        await doc_ref.set(r, merge=True)
        print(f"  [OK] Saved {r['id']} ({r['title']})")
    print("Done!")

if __name__ == "__main__":
    asyncio.run(seed())
