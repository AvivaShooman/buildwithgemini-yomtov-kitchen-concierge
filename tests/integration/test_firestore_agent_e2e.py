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

"""End-to-end integration test verifying the agent queries the live Firestore recipe catalog."""

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent
from app.app_utils.services import get_memory_service


@pytest.mark.asyncio
async def test_agent_searches_firestore_recipes():
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
        user_id="firestore_test_user",
    )

    # Prompt the agent for a Rosh Hashanah main dish that survives extended warming on the blech
    user_msg = "What main meat dishes do you have in the recipe catalog that work for Rosh Hashanah and can sit on the blech for 18+ hours?"
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_msg)],
    )

    response_text = ""
    async for event in runner.run_async(
        session_id=session.id,
        user_id="firestore_test_user",
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    assert len(response_text) > 0
    lower_resp = response_text.lower()
    # Agent should find Brisket or Chicken from Firestore
    assert "brisket" in lower_resp or "chicken" in lower_resp or "flanken" in lower_resp
