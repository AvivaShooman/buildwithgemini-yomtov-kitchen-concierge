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

"""Image generation tools for YomTov Kitchen Concierge.

Generates appetizing recipe imagery, visual blech heat zone maps, and holiday
meal timelines using the gemini-3.1-flash-lite-image model in the global region.
Saves artifacts to the ADK session (for the Playground's Artifacts panel) and
uploads directly to the public Cloud Storage bucket without writing to local disk.
"""

from __future__ import annotations

import inspect
import logging
import re
import uuid
from typing import Any

from google import genai
from google.adk.tools import ToolContext
from google.cloud import storage
from google.genai import types

logger = logging.getLogger(__name__)

# Hardcoded project ID and public bucket name as required per platform constraints
PROJECT_ID = "qwiklabs-gcp-04-ded35b1abcfb"
BUCKET_NAME = "yomtov-rag-qwiklabs-gcp-04-ded35b1abcfb"
MODEL_NAME = "gemini-3.1-flash-lite-image"
LOCATION = "global"

_storage_client: storage.Client | None = None
_genai_client: genai.Client | None = None


def get_storage_client() -> storage.Client:
    """Returns a storage.Client bound to the hardcoded project ID."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


def get_genai_client() -> genai.Client:
    """Returns a genai.Client bound to Vertex AI in the global region."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION,
        )
    return _genai_client


async def generate_holiday_image(
    prompt: str,
    item_type: str = "recipe",
    filename: str | None = None,
    tool_context: ToolContext | None = None,
) -> str:
    """Generates an image for a holiday dish, blech warming timeline, or presentation preview.

    Uses the gemini-3.1-flash-lite-image model in the global region to produce images.
    The generated image bytes are:
    1. Saved as an artifact in the session via tool_context.save_artifact (visible in the Playground's Artifacts panel).
    2. Uploaded directly to the public Cloud Storage bucket without writing to local files.

    Args:
        prompt: Description of the image to generate (e.g. 'Golden-brown classic potato kugel on a festive Yom Tov platter',
                'Visual timeline showing Friday dinner through Sunday lunch with blech placement icons',
                'Braised flanken brisket garnished with fresh rosemary and glazed carrots').
        item_type: Category of the visual ('recipe', 'blech_layout', 'timeline', 'presentation').
        filename: Optional custom filename for the artifact and object (e.g. 'potato_kugel.jpg').
                  If omitted, a unique filename is generated from the prompt.
        tool_context: Tool execution context injected by ADK.

    Returns:
        The public HTTPS URL of the uploaded image (https://storage.googleapis.com/<bucket>/<object>).
    """
    client = get_genai_client()

    # Contextualize prompt for holiday presentation if brief
    full_prompt = prompt.strip()
    if item_type == "recipe" and "photo" not in full_prompt.lower() and "kosher" not in full_prompt.lower():
        full_prompt = (
            f"Professional appetizing food photography of {full_prompt}, kosher Jewish holiday feast presentation, "
            f"festive table setting, natural warm lighting, high quality."
        )
    elif item_type == "blech_layout" or "blech" in full_prompt.lower():
        full_prompt = (
            f"Clear graphic schematic diagram of a Shabbat and Yom Tov blech hotplate layout: {full_prompt}, "
            f"showing heat zones (center direct boil, perimeter keep-warm), covered knobs, and labeled pots."
        )
    elif item_type == "timeline":
        full_prompt = (
            f"Clean visual infographic culinary timeline for Jewish holiday meals: {full_prompt}, "
            f"showing meal sequences, dish icons, and warming schedule."
        )

    logger.info("Generating image with %s in %s for prompt: %s", MODEL_NAME, LOCATION, full_prompt)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    # Extract image bytes and MIME type from response
    image_bytes: bytes | None = None
    mime_type = "image/jpeg"

    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

    if not image_bytes:
        raise RuntimeError(f"Model {MODEL_NAME} did not return any image data for prompt: {prompt}")

    # Determine extension and sanitized filename
    ext = "jpg" if "jpeg" in mime_type or "jpg" in mime_type else "png"
    if not filename:
        slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower()[:32]).strip("_") or "holiday_image"
        unique_id = uuid.uuid4().hex[:8]
        filename = f"{slug}_{unique_id}.{ext}"
    else:
        # Sanitize filename
        filename = re.sub(r"[^a-zA-Z0-9_.-]+", "_", filename).strip("_")
        if not (filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png")):
            filename = f"{filename}.{ext}"

    # 1. Save artifact in session via tool_context (Playground Artifacts panel)
    if tool_context is not None and hasattr(tool_context, "save_artifact"):
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            res = tool_context.save_artifact(filename=filename, artifact=artifact_part)
            if inspect.isawaitable(res):
                await res
            logger.info("Saved artifact %s to tool_context", filename)
        except Exception as e:
            logger.warning("Failed to save artifact to tool_context: %s", e)

    # 2. Upload in-memory image bytes to public Cloud Storage bucket
    storage_cli = get_storage_client()
    bucket = storage_cli.bucket(BUCKET_NAME)
    blob_path = f"images/{filename}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_path}"
    logger.info("Uploaded image to %s", public_url)

    return public_url
