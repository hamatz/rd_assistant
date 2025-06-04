from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from typing import Dict

from ..core.visualizer import RequirementsVisualizer

from ..config import Config
from ..llm.service import LLMServiceFactory
from ..core.analyzer import RequirementAnalyzer
from ..core.storage import SessionStorage

# Load environment variables from .env file if present
load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/sessions/{session_id}/visualization")
async def session_visualization(session_id: str, diagram_type: str = "mindmap") -> Dict[str, str]:
    """Return Mermaid diagram text for the given session."""
    analyzer = _sessions.get(session_id)
    if not analyzer:
        raise HTTPException(status_code=404, detail="Session not found")
    visualizer = RequirementsVisualizer()
    if diagram_type == "flowchart":
        diagram = visualizer.generate_flowchart(analyzer.memory)
    else:
        diagram = visualizer.generate_mindmap(analyzer.memory)
    return {"diagram": diagram}

# Expose sessions dictionary for testing
sessions = _sessions
