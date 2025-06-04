from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from typing import Dict

from ..config import Config
from ..llm.service import LLMServiceFactory
from ..core.analyzer import RequirementAnalyzer
from ..core.storage import SessionStorage

app = FastAPI()

# Initialize core services
config = Config()
llm_service = LLMServiceFactory.create(config.get_llm_config())
storage = SessionStorage(config.get_session_config().get('save_dir', 'sessions'))

# In-memory session storage
_sessions: Dict[str, RequirementAnalyzer] = {}

class MessagePayload(BaseModel):
    message: str

@app.post("/sessions")
async def create_session() -> Dict[str, str]:
    """Create a new analyzer session and return its ID."""
    session_id = str(uuid4())
    analyzer = RequirementAnalyzer(llm_service)
    _sessions[session_id] = analyzer
    # Persist empty session
    storage.save_session(analyzer.memory)
    return {"session_id": session_id}

@app.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, payload: MessagePayload) -> Dict:
    """Send a user message to the analyzer and return the result."""
    analyzer = _sessions.get(session_id)
    if not analyzer:
        raise HTTPException(status_code=404, detail="Session not found")
    response = await analyzer.process_input(payload.message)
    storage.save_session(analyzer.memory)
    return {"result": response}

@app.get("/sessions/{session_id}/status")
async def session_status(session_id: str) -> Dict:
    """Return summary status for the given session."""
    analyzer = _sessions.get(session_id)
    if not analyzer:
        raise HTTPException(status_code=404, detail="Session not found")
    return analyzer.get_current_status()

# Expose sessions dictionary for testing
sessions = _sessions
