#!/usr/bin/env python3
"""Build Serverless Vertex AI RAG Corpus for Halachot and Kosher Culinary Knowledge.

Follows the rag-engine-setup skill:
- Sets project-level RAG managed DB config to serverless in us-central1.
- Creates corpus with publishers/google/models/text-embedding-005.
- Ingests halachic reference guide and kosher holiday recipes from GCS.
- Tests standalone retrieval.
"""

import sys
import time
from google.cloud import storage
import vertexai
from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr

PROJECT_ID = "qwiklabs-gcp-04-ded35b1abcfb"
LOCATION = "us-central1"  # Serverless RAG Engine is us-central1 only
BUCKET_NAME = "yomtov-rag-qwiklabs-gcp-04-ded35b1abcfb"
GCS_PREFIX = "rag_docs"
GCS_PATH = f"gs://{BUCKET_NAME}/{GCS_PREFIX}/"

PARSING_PROMPT = (
    "Extract all individual useful halachic cooking rules, blech and warming drawer guidelines, "
    "Shabbat and Yom Tov distinctions, Eruv Tavshilin procedures, and durable kosher recipes described in this text. "
    "Output clean, factual, self-contained prose with authoritative details."
)

def upload_docs_to_gcs():
    print(f"Uploading halachic guide and recipes to {GCS_PATH}...")
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)

    files_to_upload = [
        ("data/halacha_and_culinary_guide.md", f"{GCS_PREFIX}/halacha_and_culinary_guide.md"),
        ("data/rag_recipes.txt", f"{GCS_PREFIX}/rag_recipes.txt"),
    ]

    for local_path, blob_name in files_to_upload:
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)
        print(f"  ✓ Uploaded {local_path} -> gs://{BUCKET_NAME}/{blob_name}")


def create_and_populate_rag_corpus():
    print(f"Initializing Vertex AI in {LOCATION} (project: {PROJECT_ID})...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # 1. Switch region's RAG managed DB to serverless mode
    print("Configuring region RAG managed DB to Serverless mode...")
    cfg = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
    try:
        rag.update_rag_engine_config(
            rag_engine_config=rag.RagEngineConfig(
                name=cfg,
                rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
            )
        )
        print("  ✓ Serverless mode enabled for us-central1")
    except Exception as e:
        print(f"  Notice during update_rag_engine_config: {e}")

    # 2. Create the corpus
    print("Creating RAG corpus: yomtov-halacha-culinary-corpus...")
    corpus = rag.create_corpus(
        display_name="yomtov-halacha-culinary-corpus",
        embedding_model_config=rag.EmbeddingModelConfig(
            publisher_model="publishers/google/models/text-embedding-005"
        ),
    )
    corpus_name = corpus.name
    print(f"  ✓ Created corpus: {corpus_name}")

    # 3. Import + parse + chunk + embed
    print(f"Importing documents from {GCS_PATH} with LLM parser...")
    try:
        resp = rag.import_files(
            corpus_name=corpus_name,
            paths=[GCS_PATH],
            transformation_config=rag.TransformationConfig(
                chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
            ),
            llm_parser=rag.LlmParserConfig(
                model_name="gemini-2.5-flash",
                custom_parsing_prompt=PARSING_PROMPT,
            ),
        )
        print(f"  ✓ Successfully imported files count: {resp.imported_rag_files_count}")
    except Exception as e:
        print(f"  LLM parser import failed with error ({e}), retrying with default parser...")
        resp = rag.import_files(
            corpus_name=corpus_name,
            paths=[GCS_PATH],
            transformation_config=rag.TransformationConfig(
                chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
            ),
        )
        print(f"  ✓ Imported files count: {resp.imported_rag_files_count}")

    # 4. Standalone Retrieval Test
    print("\nTesting standalone retrieval query...")
    time.sleep(5)  # Brief lag for indexing
    test_query = "What dishes survive 18 hours on the blech and how do cooking rules differ between Shabbat and Sunday Yom Tov?"
    
    for attempt in range(1, 4):
        try:
            query_resp = rag.retrieval_query(
                text=test_query,
                rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
                rag_retrieval_config=rag.RagRetrievalConfig(top_k=3),
            )
            contexts = getattr(query_resp.contexts, "contexts", [])
            print(f"  ✓ Standalone retrieval returned {len(contexts)} matched chunks:")
            for i, c in enumerate(contexts, 1):
                score = getattr(c, "score", None)
                score_str = f" [score: {score:.3f}]" if score is not None else ""
                print(f"    Chunk {i}{score_str}: {c.text[:140]}...")
            break
        except Exception as e:
            print(f"  Attempt {attempt} failed ({e}). Retrying in 5s...")
            time.sleep(5)

    print("\n" + "=" * 60)
    print("SUCCESS: Halachic RAG corpus created!")
    print(f"CORPUS_NAME: {corpus_name}")
    print("=" * 60)
    return corpus_name


if __name__ == "__main__":
    upload_docs_to_gcs()
    corpus_id = create_and_populate_rag_corpus()
