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
async def test_agent_consults_halachic_rag():
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
        user_id="halacha_tester",
    )

    user_msg = "How do cooking rules differ between Shabbat and Yom Tov, including flame transfer and Eruv Tavshilin?"
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_msg)],
    )

    response_text = ""
    async for event in runner.run_async(
        session_id=session.id,
        user_id="halacha_tester",
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text
                elif part.inline_data and part.inline_data.data:
                    response_text += part.inline_data.data.decode("utf-8", errors="ignore")

    assert len(response_text) > 0
    lower_resp = response_text.lower()
    # Check that halachic concepts are cited
    assert any(term in lower_resp for term in ["ochel nefesh", "flame", "eruv tavshilin", "shabbat", "yom tov"])


@pytest.mark.asyncio
async def test_agent_generates_blech_schedule_card():
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
        user_id="blech_tester",
    )

    user_msg = "Generate a blech schedule for Sweet Braised Brisket and Potato Kugel for Shabbat dinner in Brooklyn NY with 18 hours warming."
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_msg)],
    )

    response_parts = []
    async for event in runner.run_async(
        session_id=session.id,
        user_id="blech_tester",
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
    assert any(term in combined for term in ["blech", "brisket", "kugel", "candle", "zone"])
