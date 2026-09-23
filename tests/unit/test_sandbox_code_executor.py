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

from app.agent import root_agent, sandbox_executor
from google.adk.code_executors.code_execution_utils import CodeExecutionInput


def test_agent_has_code_executor():
    """Verify that root_agent has the AgentEngineSandboxCodeExecutor attached."""
    assert root_agent.code_executor is not None
    assert root_agent.code_executor == sandbox_executor
    assert "reasoningEngines" in sandbox_executor.sandbox_resource_name
    assert "sandboxEnvironments" in sandbox_executor.sandbox_resource_name


def test_sandbox_code_executor_run():
    """Execute Python code in the Vertex AI Agent Engine sandbox."""
    test_code = (
        "hours = 20\n"
        "rate = 0.05\n"
        "added_liquid = hours * rate\n"
        "print(f'Liquid adjustment: {added_liquid} cups')\n"
    )
    result = sandbox_executor.execute_code(None, CodeExecutionInput(code=test_code))
    assert result is not None
    assert "Liquid adjustment: 1.0 cups" in result.stdout
