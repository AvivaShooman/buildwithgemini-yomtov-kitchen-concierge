import cloudpickle
from app.agent import root_agent, app

def test_agent_and_app_cloudpickle_serialization():
    data = cloudpickle.dumps(root_agent)
    assert len(data) > 0
    restored_agent = cloudpickle.loads(data)
    assert restored_agent.name == "root_agent"

    app_data = cloudpickle.dumps(app)
    assert len(app_data) > 0
    restored_app = cloudpickle.loads(app_data)
    assert restored_app.name == "app"
