from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from .vision import ProjectVision, FeaturePriority
from .history import ChangeHistoryManager

@dataclass
class Requirement:
    content: str
    type: str
    confidence: float
    rationale: str
    implicit: bool
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

@dataclass
class Constraint:
    content: str
    type: str
    impact: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

@dataclass
class Risk:
    description: str
    severity: str
    mitigation: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

@dataclass
class ConversationMemory:
    project_name: str = ""
    project_description: str = ""
    project_vision: Optional[ProjectVision] = None
    requirements: List[Requirement] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    risks: List[Risk] = field(default_factory=list)
    key_decisions: List[Dict] = field(default_factory=list)
    current_focus: Optional[str] = None
    feature_priorities: List[FeaturePriority] = field(default_factory=list)
    history_manager: ChangeHistoryManager = field(default_factory=ChangeHistoryManager)
    
    def add_requirement(self, requirement_data: Dict):
        """要件を追加"""
        requirement = Requirement(
            content=requirement_data["content"],
            type=requirement_data["type"],
            confidence=requirement_data["confidence"],
            rationale=requirement_data["rationale"],
            implicit=requirement_data["implicit"]
        )
        self.requirements.append(requirement)

        self.history_manager.record_change(
            action='add',
            target_type='requirement',
            target_id=requirement.content,
            details=requirement_data
        )
    
    def update_requirement(self, old_req: Requirement, new_data: Dict):
        """要件を更新"""
        old_data = {
            "content": old_req.content,
            "type": old_req.type,
            "rationale": old_req.rationale,
            "metadata": old_req.metadata
        }
        
        for key, value in new_data.items():
            setattr(old_req, key, value)
        
        self.history_manager.record_change(
            action='update',
            target_type='requirement',
            target_id=old_req.content,
            details={
                "old_value": old_data,
                "new_value": new_data
            }
        )
    
    def add_constraint(self, constraint_data: Dict):
        """制約を追加"""
        constraint = Constraint(
            content=constraint_data["content"],
            type=constraint_data["type"],
            impact=constraint_data["impact"]
        )
        self.constraints.append(constraint)
    
    def add_risk(self, risk_data: Dict):
        """リスクを追加"""
        risk = Risk(
            description=risk_data["description"],
            severity=risk_data["severity"],
            mitigation=risk_data["mitigation"]
        )
        self.risks.append(risk)
    
    def update_focus(self, new_focus: str):
        """現在の焦点を更新"""
        self.current_focus = new_focus
    
    def add_decision(self, decision: Dict):
        """決定事項を追加"""
        self.key_decisions.append({
            **decision,
            "created_at": datetime.now()
        })

    def record_review(self, req: Requirement, quality_score: float, suggestions: List[str]):
            """レビュー結果を記録"""
            self.history_manager.record_change(
                action='review',
                target_type='requirement',
                target_id=req.content,
                details={
                    "review_score": quality_score,
                    "suggestions": suggestions
                }
            )
    
    def record_organization(self, changes: List[Dict]):
        """要件の再整理を記録"""
        self.history_manager.record_change(
            action='organize',
            target_type='requirements',
            target_id='bulk_update',
            details={"changes": changes}
        )

    def update_vision(self, vision: ProjectVision):
        """プロジェクトビジョンを更新"""
        old_vision = self.project_vision
        self.project_vision = vision
        
        self.history_manager.record_change(
            action='update',
            target_type='vision',
            target_id='project_vision',
            details={
                "old_value": vars(old_vision) if old_vision else None,
                "new_value": vars(vision)
            }
        )
        
        for constraint in vision.constraints:
            if not any(c.content == constraint for c in self.constraints):
                self.constraints.append(Constraint(
                    content=constraint,
                    type="business",
                    impact="ビジョンから導出された制約"
                ))
    
    def update_priorities(self, priorities: List[FeaturePriority]):
        """機能の優先順位を更新"""
        self.feature_priorities = priorities
        
        priority_map = {p.feature: p.priority for p in priorities}
        for req in self.requirements:
            if req.content in priority_map:
                req.metadata = req.metadata or {}
                req.metadata['priority'] = priority_map[req.content]

    def to_prompt_context(self) -> Dict:
        """LLMプロンプト用のコンテキストを生成"""
        context = {
            "project_name": self.project_name,
            "description": self.project_description,
            "requirements": [
                {
                    "content": req.content,
                    "type": req.type,
                    "implicit": req.implicit
                }
                for req in self.requirements
            ],
            "constraints": [
                {
                    "content": const.content,
                    "type": const.type,
                    "impact": const.impact
                }
                for const in self.constraints
            ],
            "key_decisions": self.key_decisions,
            "current_focus": self.current_focus
        }

        if self.project_vision:
            context["vision"] = {
                "goals": self.project_vision.goals,
                "success_criteria": self.project_vision.success_criteria,
                "target_users": self.project_vision.target_users,
                "constraints": self.project_vision.constraints,
                "priorities": self.project_vision.priorities
            }

        return context