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

"""Scrape and download kosher holiday recipes from Melinda Strauss, Naomi Nachman, and Ruhama's Food."""

import html
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent / "data"
RECIPES_DIR = DATA_DIR / "recipes"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RECIPES_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def download_melinda_strauss() -> list[dict]:
    print("Downloading recipes from Melinda Strauss...")
    recipes = []
    try:
        url = "https://melindastrauss.com/wp-json/wp/v2/posts?per_page=15"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        posts = resp.json()

        for post in posts:
            title = clean_text(post.get("title", {}).get("rendered", ""))
            link = post.get("link", "")
            raw_html = post.get("content", {}).get("rendered", "")
            soup = BeautifulSoup(raw_html, "html.parser")

            # Exclude non-recipe articles
            if any(skip in title.lower() for skip in ["restaurants in israel", "what is kosher", "amazon links"]):
                continue

            text_content = clean_text(soup.get_text("\n", strip=True))
            if len(text_content) < 150:
                continue

            slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
            entry = {
                "title": title,
                "author": "Melinda Strauss",
                "source_url": link,
                "content": text_content,
                "slug": f"melinda_{slug}",
            }
            recipes.append(entry)
            print(f"  + [Melinda Strauss] {title} ({len(text_content)} chars)")
    except Exception as e:
        print(f"Error downloading Melinda Strauss: {e}")
    return recipes


def download_naomi_nachman() -> list[dict]:
    print("Downloading recipes from Naomi Nachman...")
    recipes = []
    try:
        url = "https://naominachman.com/wp-json/wp/v2/posts?per_page=15"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        posts = resp.json()

        for post in posts:
            title = clean_text(post.get("title", {}).get("rendered", ""))
            link = post.get("link", "")
            raw_html = post.get("content", {}).get("rendered", "")
            soup = BeautifulSoup(raw_html, "html.parser")

            if any(skip in title.lower() for skip in ["introducing my debut", "perfect flavors: new cookbook"]):
                continue

            text_content = clean_text(soup.get_text("\n", strip=True))
            if len(text_content) < 100:
                continue

            slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
            entry = {
                "title": title,
                "author": "Naomi Nachman (The Aussie Gourmet)",
                "source_url": link,
                "content": text_content,
                "slug": f"naomi_{slug}",
            }
            recipes.append(entry)
            print(f"  + [Naomi Nachman] {title} ({len(text_content)} chars)")
    except Exception as e:
        print(f"Error downloading Naomi Nachman: {e}")
    return recipes


def download_ruhamas_food() -> list[dict]:
    print("Downloading recipes from Ruhama's Food...")
    recipes = []
    target_slugs = [
        "apple-honey-baklava",
        "round-beef-and-potato-bourekas",
        "challaganush",
        "cabbage-and-pomegranate-salad",
        "rosh-hashanah-simanim-salad",
        "festive-beef-stuffed-artichoke",
        "festive-one-pan-salmon-and-veggies",
        "beet-and-pomegranate-salad",
        "family-style-beef-bourekas",
        "fall-soup",
        "dairy-free-gluten-free-chocolate-cake",
        "celery-dates-arugula-salad",
        "cucumber-and-avocado-salad",
        "chicken-kebabs",
        "aruk-iraqi-latkes",
    ]

    for slug in target_slugs:
        try:
            url = f"https://ruhamasfood.com/recipes/{slug}"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            h1 = soup.find("h1")
            title = clean_text(h1.get_text()) if h1 else slug.replace("-", " ").title()

            # Extract ingredients and instructions
            sections = []
            for h2 in soup.find_all("h2"):
                header_title = h2.get_text(strip=True)
                if any(k in header_title.lower() for k in ["ingredient", "instruction"]):
                    next_el = h2.find_next(["ul", "ol", "p"])
                    if next_el:
                        items = [li.get_text(strip=True) for li in next_el.find_all("li")]
                        if items:
                            sections.append(f"### {header_title}\n" + "\n".join(f"- {it}" for it in items))
                        else:
                            sections.append(f"### {header_title}\n{next_el.get_text(strip=True)}")

            # Fallback to main content if specific headers missed
            if not sections:
                main = soup.find("main")
                body_text = clean_text(main.get_text("\n", strip=True)) if main else ""
            else:
                body_text = "\n\n".join(sections)

            if len(body_text) < 100:
                continue

            entry = {
                "title": title,
                "author": "Ruhama Shitrit (RuhamasFood)",
                "source_url": url,
                "content": body_text,
                "slug": f"ruhama_{slug.replace('-', '_')}",
            }
            recipes.append(entry)
            print(f"  + [Ruhama's Food] {title} ({len(body_text)} chars)")
        except Exception as e:
            print(f"  Error fetching Ruhama recipe {slug}: {e}")
    return recipes


def main():
    all_recipes = []
    all_recipes.extend(download_melinda_strauss())
    all_recipes.extend(download_naomi_nachman())
    all_recipes.extend(download_ruhamas_food())

    print(f"\nTotal recipes collected: {len(all_recipes)}")

    # Write individual markdown files
    for r in all_recipes:
        md_file = RECIPES_DIR / f"{r['slug']}.md"
        content = (
            f"# {r['title']}\n\n"
            f"**Author / Source:** {r['author']}\n"
            f"**URL:** {r['source_url']}\n\n"
            f"## Content & Preparation\n\n"
            f"{r['content']}\n"
        )
        md_file.write_text(content, encoding="utf-8")

    # Consolidate into single corpus document for RAG ingestion
    corpus_file = DATA_DIR / "rag_recipes.txt"
    blocks = []
    for r in all_recipes:
        block = (
            f"=== RECIPE: {r['title']} ===\n"
            f"Author: {r['author']}\n"
            f"Source URL: {r['source_url']}\n\n"
            f"{r['content']}\n"
            f"=== END RECIPE ===\n"
        )
        blocks.append(block)

    corpus_file.write_text("\n\n".join(blocks), encoding="utf-8")
    print(f"Saved consolidated corpus file to: {corpus_file} ({corpus_file.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
