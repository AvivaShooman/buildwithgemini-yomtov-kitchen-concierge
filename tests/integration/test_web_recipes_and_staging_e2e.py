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

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from app.agent import root_agent
from app.app_utils.services import get_memory_service


@pytest.mark.asyncio
async def test_agent_shares_recipe_in_plain_text():
    session_service = InMemorySessionService()
    memory_service = get_memory_service()
    runner = Runner(
        agent=root_agent,
        app_name="yomtov-kitchen-concierge",
        session_service=session_service,
        memory_service=memory_service,
    )

    session = await session_service.create_session(
        app_name="yomtov-kitchen-concierge",
        user_id="plain_text_tester",
    )

    user_msg = "Please share the recipe for Sweet Braised Brisket in plain text with ingredients and directions."
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_msg)],
    )

    response_text = ""
    async for event in runner.run_async(
        session_id=session.id,
        user_id="plain_text_tester",
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    assert len(response_text) > 0
    lower_resp = response_text.lower()
    # Check that plain text recipe with ingredients and directions is presented
    assert "brisket" in lower_resp
    assert any(term in lower_resp for term in ["ingredient", "cup", "onion", "tablespoon", "beef"])
    assert any(term in lower_resp for term in ["direction", "instruction", "step", "cook", "braise"])


@pytest.mark.asyncio
async def test_agent_staging_schedule_with_location_and_year():
    session_service = InMemorySessionService()
    memory_service = get_memory_service()
    runner = Runner(
        agent=root_agent,
        app_name="yomtov-kitchen-concierge",
        session_service=session_service,
        memory_service=memory_service,
    )

    session = await session_service.create_session(
        app_name="yomtov-kitchen-concierge",
        user_id="staging_tester",
    )

    user_msg = "Plan when to put brisket and potato kugel on the blech or in the warming drawer for Shabbat in Brooklyn, NY for 2026."
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_msg)],
    )

    response_parts = []
    async for event in runner.run_async(
        session_id=session.id,
        user_id="staging_tester",
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_parts.append(part.text)
                elif part.inline_data and part.inline_data.data:
                    response_parts.append(part.inline_data.data.decode("utf-8", errors="ignore"))

    combined = " ".join(response_parts).lower()
    assert len(combined) > 0
    assert any(term in combined for term in ["candle lighting", "lighting", "blech", "warming drawer"])
    assert any(term in combined for term in ["brooklyn", "phase", "pre-heat", "cutoff", "before"])


@pytest.mark.asyncio
async def test_agent_searches_web_for_unseen_kosher_recipe():
    session_service = InMemorySessionService()
    memory_service = get_memory_service()
    runner = Runner(
        agent=root_agent,
        app_name="yomtov-kitchen-concierge",
        session_service=session_service,
        memory_service=memory_service,
    )

    session = await session_service.create_session(
        app_name="yomtov-kitchen-concierge",
        user_id="web_recipe_tester",
    )

    user_msg = "We don't have a recipe for Yemenite Hilbeh or Moroccan Lamb Tagine saved. Can you search the web for a kosher recipe for Moroccan Lamb Tagine and share it in plain text?"
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_msg)],
    )

    response_parts = []
    async for event in runner.run_async(
        session_id=session.id,
        user_id="web_recipe_tester",
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_parts.append(part.text)

    combined = " ".join(response_parts).lower()
    assert len(combined) > 0
    assert any(term in combined for term in ["tagine", "lamb"])
    assert any(term in combined for term in ["kosher", "ingredient", "apricot", "spice", "broth"])
