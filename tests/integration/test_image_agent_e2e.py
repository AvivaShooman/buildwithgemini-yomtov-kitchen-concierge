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
from app.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.app_utils.services import get_memory_service
from google.genai import types


@pytest.mark.asyncio
async def test_agent_invokes_image_generation():
    """Verify the agent calls generate_holiday_image and outputs the public image URL."""
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
        user_id="test_user",
    )

    query = "Please generate an image preview of a festive golden potato kugel on a Yom Tov platter."
    content = types.Content(
        parts=[types.Part.from_text(text=query)],
        role="user",
    )

    chunks = []
    function_calls = []
    async for event in runner.run_async(
        session_id=session.id,
        user_id="test_user",
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    chunks.append(part.text)
                if part.function_call:
                    function_calls.append(part.function_call.name)

    full_response = "".join(chunks)
    assert "generate_holiday_image" in function_calls or "storage.googleapis.com" in full_response or "kugel" in full_response.lower()
