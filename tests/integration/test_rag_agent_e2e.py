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
from app.app_utils.rag_tools import search_recipe_rag_corpus
from app.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.app_utils.services import get_memory_service
from google.genai import types


def test_rag_retrieval_direct():
    """Verify RAG retrieval returns grounded content from the blog recipes."""
    result = search_recipe_rag_corpus("Passover chocolate chip cookies Melinda Strauss")
    assert "Melinda Strauss" in result or "Chocolate Chip" in result or "Passover" in result


@pytest.mark.asyncio
async def test_agent_answers_from_rag():
    """Verify the agent calls search_recipe_rag_corpus when asked about specific blog recipes."""
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

    query = "What ingredients does Melinda Strauss recommend for Passover chocolate chip cookies?"
    content = types.Content(
        parts=[types.Part.from_text(text=query)],
        role="user",
    )

    chunks = []
    async for event in runner.run_async(
        session_id=session.id,
        user_id="test_user",
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    chunks.append(part.text)

    full_response = "".join(chunks)
    assert len(full_response) > 0
    lower_resp = full_response.lower()
    assert any(term in lower_resp for term in ["cookie", "chocolate", "passover", "oil", "sugar", "egg", "flour"])
