from typing import Dict, Optional
from pathlib import Path
from datetime import datetime
import os
from dataclasses import asdict
from .memory import ConversationMemory, Requirement, Constraint, Risk
from .session_utils import SessionUtils
from .types import UnderstandingStatus 

class SessionStorage:
    def __init__(self, base_dir: str = "sessions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.utils = SessionUtils()

    def save_session(self, memory: ConversationMemory) -> str:
        """セッションをJSONとして保存"""
        from dataclasses import asdict
        try:
            safe_name = memory.project_name.replace(" ", "_").lower() or "unnamed_project"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_name}_{timestamp}.json"

            session_data = {
                "project_name": memory.project_name,
                "project_description": memory.project_description,
                "requirements": [asdict(req) for req in memory.requirements],
                "constraints": [asdict(const) for const in memory.constraints],
                "risks": [asdict(risk) for risk in memory.risks],
                "key_decisions": memory.key_decisions,
                "current_focus": memory.current_focus,
                "saved_at": timestamp
            }

            if memory.project_vision:
                session_data["project_vision"] = {
                    "goals": memory.project_vision.goals,
                    "success_criteria": memory.project_vision.success_criteria,
                    "target_users": memory.project_vision.target_users,
                    "constraints": memory.project_vision.constraints,
                    "priorities": memory.project_vision.priorities
                }
            
            if memory.feature_priorities:
                from dataclasses import asdict
                session_data["feature_priorities"] = [asdict(fp) for fp in memory.feature_priorities]

            if memory.understanding_history:
                session_data["understanding_history"] = [
                    asdict(status) for status in memory.understanding_history
                ]

            file_path = self.base_dir / filename
            self.utils.dump_json(session_data, file_path)
            
            return str(file_path)
            
        except Exception as e:
            self.utils.logger.error(f"セッション保存中にエラーが発生しました: {str(e)}", exc_info=True)
            raise

    def load_session(self, file_path: str) -> ConversationMemory:
        """保存されたセッションを読み込み"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"セッションファイルが見つかりません: {file_path}")
            
            data = self.utils.load_json(path)
            
            memory = ConversationMemory(
                project_name=data["project_name"],
                project_description=data["project_description"],
                current_focus=data.get("current_focus")
            )

            if "project_vision" in data:
                vision_data = data["project_vision"]
                from .vision import ProjectVision
                memory.project_vision = ProjectVision(
                    goals=vision_data.get("goals", []),
                    success_criteria=vision_data.get("success_criteria", []),
                    target_users=vision_data.get("target_users", []),
                    constraints=vision_data.get("constraints", []),
                    priorities=vision_data.get("priorities", {})
                )

            for req_data in data["requirements"]:
                memory.requirements.append(Requirement(**req_data))
            
            for const_data in data["constraints"]:
                memory.constraints.append(Constraint(**const_data))
            
            for risk_data in data["risks"]:
                memory.risks.append(Risk(**risk_data))
            
            memory.key_decisions = data["key_decisions"]
            
            if "feature_priorities" in data:
                from .vision import FeaturePriority
                for fp_data in data["feature_priorities"]:
                    memory.feature_priorities.append(FeaturePriority(**fp_data))

            if "understanding_history" in data:
                for status_data in data["understanding_history"]:
                    memory.understanding_history.append(UnderstandingStatus(**status_data))

            return memory
            
        except Exception as e:
            self.utils.logger.error(f"セッション読み込み中にエラーが発生しました: {str(e)}", exc_info=True)
            raise

    def list_sessions(self, project_name: Optional[str] = None) -> list:
        """保存されているセッションの一覧を取得"""
        sessions = []
        for file in self.base_dir.glob("*.json"):
            try:
                data = self.utils.load_json(file)
                
                if project_name is None or project_name.lower() in data["project_name"].lower():
                    sessions.append({
                        "file_path": str(file),
                        "project_name": data["project_name"],
                        "saved_at": data["saved_at"],
                        "requirements_count": len(data["requirements"]),
                        "constraints_count": len(data["constraints"]),
                        "risks_count": len(data["risks"])
                    })
            except Exception as e:
                self.utils.logger.warning(f"セッションファイル {file} の読み込みに失敗: {str(e)}")
                continue
        
        return sorted(sessions, key=lambda x: x["saved_at"], reverse=True)