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

"""RAG retrieval tool for authentic Jewish holiday recipes.

Grounds the YomTov Kitchen Concierge on scraped kosher recipes from:
- Melinda Strauss (melindastrauss.com)
- Naomi Nachman / The Aussie Gourmet (naominachman.com)
- Ruhama Shitrit / Ruhama's Food (ruhamasfood.com)
"""

import os
from pathlib import Path
import agentplatform

PROJECT_ID = "qwiklabs-gcp-04-ded35b1abcfb"
LOCATION = "europe-west4"
CORPUS_NAME = "projects/821049907373/locations/europe-west4/ragCorpora/6917529027641081856"


def search_recipe_rag_corpus(query: str) -> str:
    """Search authentic Jewish holiday recipes, preparation steps, and culinary ideas
    from prominent kosher food blogs (Melinda Strauss, Naomi Nachman, and Ruhama's Food)
    via the Vertex AI RAG Engine.

    Use this tool when users ask for authentic kosher recipes, Yom Tov or Shabbat dish ideas,
    holiday desserts (e.g. Passover cookies, honey cheesecake, babka buns), savory mains
    (e.g. veal roast, stuffed artichokes, pastrami meatballs), salads, or latkes.

    Args:
        query: Search keywords for ingredients, dishes, holidays (e.g., 'Passover chocolate chip cookies',
               'Rosh Hashanah simanim salad', 'veal roast with mushroom sauce', 'bourekas').

    Returns:
        Grounded recipe excerpts, authors, ingredients, and instructions from the RAG corpus.
    """
    try:
        client = agentplatform.Client(project=PROJECT_ID, location=LOCATION)
        response = client.rag.retrieve_contexts(
            vertex_rag_store=dict(
                rag_resources=[dict(rag_corpus=CORPUS_NAME)]
            ),
            query=dict(text=query, similarity_top_k=3),
        )
        contexts = getattr(response.contexts, "contexts", [])
        if not contexts:
            return f"No recipes found in the blog RAG corpus for query: '{query}'."

        results = []
        for i, ctx in enumerate(contexts, 1):
            text = ctx.text.strip()
            score = getattr(ctx, "score", None)
            score_header = f" (relevance score: {score:.2f})" if score is not None else ""
            results.append(f"### [Recipe Source {i}]{score_header}\n{text}")

        return "\n\n".join(results)
    except Exception as e:
        # Fallback to local recipe cache if remote call encounters transient connectivity
        local_dir = Path(__file__).resolve().parent.parent.parent / "data" / "recipes"
        if local_dir.exists():
            matched = []
            keywords = [w.lower() for w in query.split() if len(w) > 3]
            for file_path in local_dir.glob("*.md"):
                content = file_path.read_text(encoding="utf-8")
                if any(k in content.lower() for k in keywords):
                    matched.append(content[:1500])
                if len(matched) >= 2:
                    break
            if matched:
                return "Note: Retrieved from local recipe cache:\n\n" + "\n\n---\n\n".join(matched)
        return f"Error retrieving from recipe RAG corpus: {str(e)}"


def consult_halachic_culinary_docs(query: str) -> str:
    """Search authoritative halachic rulings, appliance standards, blech management, and holiday guidelines
    from the YomTov Kitchen Concierge Halachic & Culinary Knowledge Base via Vertex AI RAG Engine.

    Use this tool whenever users ask:
    - How cooking rules differ between Shabbat and Yom Tov (Ochel Nefesh, pre-existing flame transfer, flame adjustment).
    - When Shabbat coincides with Yom Tov (Shabbat restrictions take 100% precedence; zero cooking or flame transfer).
    - Eruv Tavshilin requirements, timing, blessing, declaration, and procedure when Yom Tov precedes Shabbat.
    - Blech halachot: Shehiya (leaving before sunset), Chazarah (5 conditions to return food), Hatmana (wrapping prohibitions).
    - Modern appliances: certified Sabbath Mode warming drawers, oven Sabbath mode, and safe temperature holding.
    - Extended blech warming durability (18-36 hours on heat), physical heat zones (Center boil vs Perimeter keep-warm),
      and braising liquid evaporation compensation.
    - Prohibition of Hachanah (preparing food or setting tables on Yom Tov Day 1 for Day 2 before Tzeit HaKochavim).

    Args:
        query: What halachic question, blech rule, or holiday kitchen procedure to look up.

    Returns:
        Authoritative halachic passages, definitions, and practical kitchen guidelines grounded in the corpus.
    """
    try:
        client = agentplatform.Client(project=PROJECT_ID, location=LOCATION)
        response = client.rag.retrieve_contexts(
            vertex_rag_store=dict(
                rag_resources=[dict(rag_corpus=CORPUS_NAME)]
            ),
            query=dict(text=query, similarity_top_k=4),
        )
        contexts = getattr(response.contexts, "contexts", [])
        if not contexts:
            return f"No halachic rulings found in the RAG corpus for query: '{query}'."

        results = []
        for i, ctx in enumerate(contexts, 1):
            text = ctx.text.strip()
            score = getattr(ctx, "score", None)
            score_header = f" (relevance score: {score:.2f})" if score is not None else ""
            results.append(f"### [Authoritative Halachic Source {i}]{score_header}\n{text}")

        return "\n\n".join(results)
    except Exception as e:
        # Local fallback to halacha_and_culinary_guide.md
        guide_path = Path(__file__).resolve().parent.parent.parent / "data" / "halacha_and_culinary_guide.md"
        if guide_path.exists():
            content = guide_path.read_text(encoding="utf-8")
            return f"Note: Retrieved from local Halachic & Culinary Guide fallback:\n\n{content[:3000]}"
        return f"Error retrieving from halachic RAG corpus: {str(e)}"

