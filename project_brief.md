# My agent: YomTov Kitchen Concierge
One-liner: A conversational agent that helps Jewish families and holiday hosts plan festive meal menus, kitchen prep timelines, blech/warming drawer management, and grocery lists tailored to guest dietary needs, multi-day leftover strategies, Chol HaMoed transitions, and halachic cooking priorities (where Shabbat rules take precedence over Yom Tov) with a catalog of warming-safe seasonal Jewish recipes and holiday schedules.

Tool coverage:
- Memory: Remembers family and guest profiles (allergies, dietary restrictions like gluten-free/nut-free, likes/dislikes, kashrut customs such as Ashkenazi vs. Sephardic / Kitniyot, meat/dairy/pareve preferences, household size, past menus, kitchen warming equipment such as blech, hot plate, or warming drawer).
- Tools:
  - lookup_jewish_calendar: Query Hebcal API / calendar for holiday dates, candle lighting times, number of Yom Tov days, Chol HaMoed intervals, and Shabbat-Yom Tov overlaps (flagging when Shabbat coincides with Yom Tov).
  - check_cooking_rules: Evaluates halachic cooking priorities and rules (Shabbat rules strictly override Yom Tov when they coincide—zero cooking or flame transfer permitted; Yom Tov allows fresh cooking for that day via pre-existing flame; Eruv Tavshilin for Yom Tov adjacent to Shabbat; no hachanah/prep from Yom Tov Day 1 for Day 2 until nightfall; halachot of placing dry vs. liquid foods on a blech/warming drawer).
  - search_recipes: Look up recipes tagged for blech/warming drawer durability (braises, briskets, kugels, stews) vs. fresh-only dishes, day 2 leftover ratings, distinct casual Chol HaMoed meal ideas, dietary restrictions, and Meat/Dairy/Pareve classification.
  - plan_blech_schedule: Calculates heat zone positioning (center boil vs. perimeter keep-warm) and hours-on-heat adjustment (extra braising liquid/sauce ratios) to prevent burning or drying out over 12-36 hour warming periods.
  - generate_grocery_list: Aggregates and consolidates ingredients scaled to guest count across all meals (Yom Tov seudot, Shabbat meals, and Chol HaMoed).
- Catalog/UI: Collection of warming-friendly recipes, multi-day meal cards (tagged with Blech-Friendly, Day 2 Reheat Quality, Course, and Kosher status), and visual timeline tables for oven/stovetop prep and blech placement.
- Image gen: Generates visual previews of festive dish presentations and multi-dish blech layout maps (optimizing space and heat zones).
- Sandbox: Computes prep timelines, blech evaporation liquid adjustments based on warming hours, and recipe portion scaling across multi-day holiday blocks.

Core rails (everyone): memory, tools, eval, deploy, frontend
My stretch menu (pick later): A2UI recipe & blech schedule cards, dish & blech layout image generation, warming duration code sandbox calculator, Vertex AI RAG Engine for Jewish culinary blogs and halachot
First eval question: "We have a 3-day holiday weekend where the first day of Yom Tov falls on Shabbat, followed by Yom Tov Day 2 on Sunday. I have a warming drawer and a blech. Plan our menus for Friday night through Sunday lunch, accounting for 2 guests with celiac disease. Tell me what dishes will survive 18+ hours on the blech, what to do with leftovers for Day 2, the exact timeline for when each dish goes onto the blech, and how cooking rules differ between Saturday and Sunday."
