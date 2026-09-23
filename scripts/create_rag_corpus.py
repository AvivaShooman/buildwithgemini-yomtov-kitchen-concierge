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

"""Create a serverless Vertex AI RAG Engine corpus and import blog recipes."""

import sys
import time
import agentplatform

PROJECT_ID = "qwiklabs-gcp-04-ded35b1abcfb"
LOCATION = "us-central1"
GCS_PATH = "gs://yomtov-rag-qwiklabs-gcp-04-ded35b1abcfb/rag/rag_recipes.txt"
CORPUS_DISPLAY_NAME = "yomtov-recipes-corpus"

PARSING_PROMPT = (
    "Extract the individual recipes, dishes, ingredients, and preparation instructions described in this text. "
    "Preserve the author name, title, holiday associations, and exact ingredients and steps. "
    "Output clean, self-contained recipe prose."
)


def main():
    print(f"Initializing agentplatform.Client (project={PROJECT_ID}, location={LOCATION})...")
    client = agentplatform.Client(project=PROJECT_ID, location=LOCATION)

    # 1. Switch the region's RAG managed DB to serverless mode (project-level, once).
    cfg_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
    print(f"Configuring RAG Engine for serverless mode: {cfg_name}...")
    try:
        client.rag.update_config(
            rag_engine_config=dict(
                name=cfg_name,
                rag_managed_db_config=dict(mode="SERVERLESS"),
            )
        )
        print("  -> RAG engine config set to serverless mode.")
    except Exception as e:
        print(f"  Note during update_rag_engine_config: {e}")

    # Check if corpus already exists
    corpus = None
    try:
        corpora = client.rag.list_corpora()
        for c in corpora:
            if getattr(c, "display_name", "") == CORPUS_DISPLAY_NAME:
                corpus = c
                print(f"Found existing corpus: {corpus.name}")
                break
    except Exception as e:
        print(f"Note checking existing corpora: {e}")

    # 2. Create the corpus if not found
    if corpus is None:
        print(f"Creating corpus '{CORPUS_DISPLAY_NAME}' with text-embedding-005...")
        corpus = client.rag.create_corpus(
            display_name=CORPUS_DISPLAY_NAME,
            description="Kosher holiday recipes from Melinda Strauss, Naomi Nachman, and Ruhama's Food",
            embedding_model_config=dict(
                publisher_model="publishers/google/models/text-embedding-005"
            ),
        )
        print(f"  -> Created corpus: {corpus.name}")

    corpus_resource_name = corpus.name

    # 3. Import + parse + chunk + embed
    print(f"Importing and indexing {GCS_PATH} into corpus {corpus_resource_name}...")
    try:
        resp = client.rag.import_files(
            corpus_name=corpus_resource_name,
            paths=[GCS_PATH],
            transformation_config=dict(
                chunking_config=dict(chunk_size=512, chunk_overlap=100)
            ),
            llm_parser=dict(
                model_name="gemini-2.5-flash",
                custom_parsing_prompt=PARSING_PROMPT,
            ),
        )
        print(f"  -> Import complete! Imported files: {getattr(resp, 'imported_rag_files_count', 'unknown')}")
    except Exception as e:
        print(f"Import with LLM parser returned: {e}")
        print("Attempting standard import without LLM parser...")
        resp = client.rag.import_files(
            corpus_name=corpus_resource_name,
            paths=[GCS_PATH],
            transformation_config=dict(
                chunking_config=dict(chunk_size=512, chunk_overlap=100)
            ),
        )
        print(f"  -> Standard import complete! Imported files: {getattr(resp, 'imported_rag_files_count', 'unknown')}")

    # 4. Standalone Retrieval Test
    print("\nTesting standalone retrieval query...")
    time.sleep(3)  # Brief wait for index readiness
    test_queries = [
        "What are the ingredients in Melinda Strauss Passover chocolate chip cookies?",
        "How does Ruhama make Apple Honey Baklava?",
        "What recipe does Naomi Nachman have for veal roast with mushroom sauce?",
    ]

    for q in test_queries:
        print(f"\n--- Query: '{q}' ---")
        try:
            res = client.rag.retrieve_contexts(
                vertex_rag_store=dict(
                    rag_resources=[dict(rag_corpus=corpus_resource_name)]
                ),
                query=dict(text=q, similarity_top_k=2),
            )
            contexts = getattr(res.contexts, "contexts", [])
            print(f"Found {len(contexts)} matched contexts:")
            for i, c in enumerate(contexts, 1):
                snippet = c.text.replace("\n", " ")[:200]
                print(f"  Context {i} (score: {getattr(c, 'score', 'N/A')}): {snippet}...")
        except Exception as e:
            print(f"Retrieval query error: {e}")

    print("\n" + "=" * 60)
    print(f"RAG Corpus successfully set up!")
    print(f"Corpus Name: {corpus_resource_name}")
    print("=" * 60)

    # Save corpus name to .env or config file
    with open(".env", "a") as f:
        f.write(f"\nRAG_CORPUS_NAME={corpus_resource_name}\n")
    print("Appended RAG_CORPUS_NAME to .env")


if __name__ == "__main__":
    main()
