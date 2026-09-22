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

"""Unit and live tests for the image generation tool."""

from __future__ import annotations

import urllib.request
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types

from app.app_utils.image_tools import (
    BUCKET_NAME,
    PROJECT_ID,
    generate_holiday_image,
)


@pytest.mark.asyncio
async def test_generate_holiday_image_unit():
    """Verifies image generation, artifact saving, GCS upload, and URL return with mocks."""
    test_bytes = b"fake_jpeg_image_bytes_content"
    test_mime = "image/jpeg"

    # Mock genai response
    mock_part = types.Part.from_bytes(data=test_bytes, mime_type=test_mime)
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]
    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]

    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.return_value = mock_response

    # Mock storage client
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage_client = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket

    # Mock ADK tool_context
    mock_tool_context = AsyncMock()

    with patch("app.app_utils.image_tools.get_genai_client", return_value=mock_genai_client), \
         patch("app.app_utils.image_tools.get_storage_client", return_value=mock_storage_client):

        url = await generate_holiday_image(
            prompt="Classic potato kugel",
            item_type="recipe",
            filename="my_kugel.jpg",
            tool_context=mock_tool_context,
        )

    # 1. Verify URL returned matches public GCS format
    expected_url = f"https://storage.googleapis.com/{BUCKET_NAME}/images/my_kugel.jpg"
    assert url == expected_url

    # 2. Verify artifact saved via tool_context
    mock_tool_context.save_artifact.assert_called_once()
    saved_call = mock_tool_context.save_artifact.call_args
    assert saved_call.kwargs["filename"] == "my_kugel.jpg"
    assert saved_call.kwargs["artifact"].inline_data.data == test_bytes

    # 3. Verify in-memory upload to GCS blob without local file writing
    mock_storage_client.bucket.assert_called_once_with(BUCKET_NAME)
    mock_bucket.blob.assert_called_once_with("images/my_kugel.jpg")
    mock_blob.upload_from_string.assert_called_once_with(test_bytes, content_type=test_mime)


@pytest.mark.asyncio
async def test_generate_holiday_image_live():
    """Live test calling gemini-3.1-flash-lite-image in global region and uploading to GCS."""
    mock_tool_context = AsyncMock()

    public_url = await generate_holiday_image(
        prompt="Golden potato latke with apple sauce",
        item_type="recipe",
        filename="live_test_latke.jpg",
        tool_context=mock_tool_context,
    )

    # Verify public URL format
    assert public_url.startswith(f"https://storage.googleapis.com/{BUCKET_NAME}/images/")
    assert public_url.endswith(".jpg")

    # Verify tool_context artifact was saved
    assert mock_tool_context.save_artifact.called

    # Verify public HTTP accessibility
    req = urllib.request.Request(public_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        content_type = resp.headers.get("Content-Type")
        assert "image" in content_type
        image_data = resp.read()
        assert len(image_data) > 1000
