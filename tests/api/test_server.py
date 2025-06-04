import os
import sys
import pytest
from httpx import AsyncClient

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from rd_assistant.api import server

@pytest.mark.asyncio
async def test_session_lifecycle(monkeypatch):
    async def fake_process_input(self, message: str):
        return {"echo": message}

    monkeypatch.setattr(server.RequirementAnalyzer, "process_input", fake_process_input)
    monkeypatch.setattr(server.storage, "save_session", lambda memory: "dummy")

    async with AsyncClient(app=server.app, base_url="http://test") as ac:
        res = await ac.post("/sessions")
        assert res.status_code == 200
        session_id = res.json()["session_id"]
        assert session_id in server.sessions

        res2 = await ac.post(f"/sessions/{session_id}/messages", json={"message": "hello"})
        assert res2.status_code == 200
        assert res2.json()["result"] == {"echo": "hello"}

        res3 = await ac.get(f"/sessions/{session_id}/status")
        assert res3.status_code == 200
        assert isinstance(res3.json(), dict)

        res4 = await ac.get(f"/sessions/{session_id}/visualization")
        assert res4.status_code == 200
        assert "mindmap" in res4.json()["diagram"]
