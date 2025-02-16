from typing import Dict, Optional
from ..llm.service import LLMService
from ..llm.prompts import PromptTemplate, ProjectContext
from .memory import ConversationMemory

class RequirementAnalyzer:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.prompt_template = PromptTemplate()
        self.memory = ConversationMemory()

    async def process_input(self, user_input: str) -> Dict:
        context = ProjectContext(
            project_name=self.memory.project_name,
            description=self.memory.project_description,
            requirements=[vars(req) for req in self.memory.requirements],
            constraints=[vars(const) for const in self.memory.constraints],
            key_decisions=self.memory.key_decisions,
            current_focus=self.memory.current_focus
        )
        
        prompt = self.prompt_template.create_prompt(user_input, context)
        response = await self.llm_service.generate_response(prompt)
        
        self._update_memory(response)
        
        return response

    def _update_memory(self, response: Dict):
        if 'analysis' in response and 'extracted_requirements' in response['analysis']:
            for req in response['analysis']['extracted_requirements']:
                if req['confidence'] > 0.7:  # 確信度の高い要件のみを記録
                    self.memory.add_requirement(req)
        
        if 'analysis' in response and 'identified_constraints' in response['analysis']:
            for constraint in response['analysis']['identified_constraints']:
                self.memory.add_constraint(constraint)
        
        if 'analysis' in response and 'potential_risks' in response['analysis']:
            for risk in response['analysis']['potential_risks']:
                self.memory.add_risk(risk)

    def get_current_status(self) -> Dict:
        """現在の分析状況を取得"""
        return {
            "requirements_count": len(self.memory.requirements),
            "constraints_count": len(self.memory.constraints),
            "risks_count": len(self.memory.risks),
            "current_focus": self.memory.current_focus
        }

    def get_requirements_summary(self) -> Dict:
        """要件の要約を取得"""
        functional_reqs = [r for r in self.memory.requirements if r.type == "functional"]
        non_functional_reqs = [r for r in self.memory.requirements if r.type == "non_functional"]
        technical_reqs = [r for r in self.memory.requirements if r.type == "technical"]
        business_reqs = [r for r in self.memory.requirements if r.type == "business"]

        return {
            "functional": {
                "count": len(functional_reqs),
                "items": functional_reqs
            },
            "non_functional": {
                "count": len(non_functional_reqs),
                "items": non_functional_reqs
            },
            "technical": {
                "count": len(technical_reqs),
                "items": technical_reqs
            },
            "business": {
                "count": len(business_reqs),
                "items": business_reqs
            }
        }

    def set_project_info(self, name: str, description: str):
        """プロジェクト情報を設定"""
        self.memory.project_name = name
        self.memory.project_description = description