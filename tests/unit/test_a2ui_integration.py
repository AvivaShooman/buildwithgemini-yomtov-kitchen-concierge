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

import json
from app.agent import root_agent, schema_manager
from app.a2ui_utils import a2ui_callback
from google.adk.models.llm_response import LlmResponse
from google.genai import types


def test_agent_a2ui_wiring():
    """Verify that root_agent has a2ui_callback wired and schema_manager initialized."""
    assert root_agent.after_model_callback == a2ui_callback
    assert schema_manager._version == "0.8"
    assert "beginRendering" in root_agent.instruction
    assert "surfaceUpdate" in root_agent.instruction
    assert "YomTov Kitchen Concierge" in root_agent.instruction


def test_a2ui_callback_rewraps_v08():
    """Verify that a2ui_callback converts raw A2UI JSON into an a2a_datapart_json blob."""
    payload = [
        {
            "beginRendering": {
                "surfaceId": "default",
                "root": "root_card",
            }
        },
        {
            "surfaceUpdate": {
                "surfaceId": "default",
                "components": [
                    {
                        "id": "root_card",
                        "component": {
                            "Card": {
                                "child": "col1"
                            }
                        }
                    },
                    {
                        "id": "col1",
                        "component": {
                            "Column": {
                                "children": {
                                    "explicitList": ["text1"]
                                }
                            }
                        }
                    },
                    {
                        "id": "text1",
                        "component": {
                            "Text": {
                                "text": {"literalString": "Rosh Hashanah Brisket Plan"},
                                "usageHint": "h1"
                            }
                        }
                    }
                ]
            }
        }
    ]

    llm_resp = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(text=json.dumps(payload))]
        )
    )

    rewrapped = a2ui_callback(None, llm_resp)
    assert rewrapped is not None
    assert rewrapped.custom_metadata == {"a2a:response": "true"}
    assert len(rewrapped.content.parts) == 2
    assert rewrapped.content.parts[0].inline_data.mime_type == "text/plain"
    assert b"<a2a_datapart_json>" in rewrapped.content.parts[0].inline_data.data
