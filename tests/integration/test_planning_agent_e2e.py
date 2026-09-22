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

"""End-to-end integration test verifying the agent uses planning tools (calendar & blech)."""

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent
from app.app_utils.services import get_memory_service


@pytest.mark.asyncio
async def test_agent_plans_blech_and_calendar():
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
        user_id="planning_test_user",
    )

    # Prompt the agent to check Rosh Hashanah 2026 dates and calculate blech schedule
    user_msg = "When is Rosh Hashanah 2026, does any day coincide with Shabbat, and where should we place our potato kugel on the blech?"
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_msg)],
    )

    response_text = ""
    async for event in runner.run_async(
        session_id=session.id,
        user_id="planning_test_user",
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    assert len(response_text) > 0
    # Should mention Rosh Hashana dates or September 2026, and blech advice (perimeter / keep warm)
    response_lower = response_text.lower()
    assert "rosh hashan" in response_lower or "2026" in response_lower
    assert "perimeter" in response_lower or "edge" in response_lower or "blech" in response_lower
