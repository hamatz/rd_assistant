from typing import List, Dict, Optional
from dataclasses import dataclass
from .memory import ConversationMemory, Requirement

@dataclass
class OrganizeResult:
    organized_requirements: List[Requirement]
    suggestions: List[str]
    changes_made: List[Dict]

class RequirementsOrganizer:
    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def organize_requirements(self, memory: ConversationMemory) -> OrganizeResult:
        """要件の再整理を行う"""
        prompt = self._create_organization_prompt(memory)
        
        try:
            response = await self.llm_service.generate_response(prompt)
            return self._parse_organization_response(response, memory)
        except Exception as e:
            print(f"要件の再整理中にエラーが発生しました: {str(e)}")
            raise

    def _create_organization_prompt(self, memory: ConversationMemory) -> str:
        """整理用のプロンプトを生成"""
        requirements_text = "\n".join([
            f"- 種類: {req.type}\n"
            f"  内容: {req.content}\n"
            f"  理由: {req.rationale}\n"
            for req in memory.requirements
        ])

        prompt_template = '''
あなたは熟練したシステムアナリストとして、以下の要件セットを再整理してください。

プロジェクト: {project_name}
概要: {project_description}

現在の要件一覧:
{requirements}

以下の点を考慮して要件を整理してください：
1. 重複する要件の統合
2. 密接に関連する要件のグループ化
3. より上位レベルの要件として一般化できるものの特定
4. 相反する要件や矛盾の解消
5. より明確で簡潔な表現への改善

応答は以下の形式のJSONで返してください：

{{
    "organized_requirements": [
        {{
            "type": "functional",
            "content": "要件の内容",
            "rationale": "この要件が必要な理由や背景",
            "confidence": 0.9,
            "source_requirements": ["元の要件のインデックス"],
            "changes_made": "この要件に対して行った変更の説明"
        }}
    ],
    "suggestions": [
        "要件の改善や追加の検討が必要な点についての提案"
    ],
    "changes_summary": [
        {{
            "type": "merge",
            "description": "変更内容の説明",
            "affected_requirements": ["影響を受けた要件のインデックス"]
        }}
    ]
}}

注意事項：
- typeは "functional", "non_functional", "technical", "business" のいずれかを指定
- confidenceは 0.0 から 1.0 の間の数値を指定
- 変更の種類（type）は "merge", "generalize", "clarify", "split" のいずれかを指定
'''

        return prompt_template.format(
            project_name=memory.project_name,
            project_description=memory.project_description,
            requirements=requirements_text
        )

    def _parse_organization_response(self, response: Dict, memory: ConversationMemory) -> OrganizeResult:
        """LLMからの応答を解析して新しい要件セットを作成"""
        organized_reqs = []
        changes_made = response.get('changes_summary', [])
        suggestions = response.get('suggestions', [])

        for req_data in response.get('organized_requirements', []):
            requirement = Requirement(
                content=req_data['content'],
                type=req_data['type'],
                confidence=float(req_data['confidence']),
                rationale=req_data['rationale'],
                implicit=False 
            )
            organized_reqs.append(requirement)

        return OrganizeResult(
            organized_requirements=organized_reqs,
            suggestions=suggestions,
            changes_made=changes_made
        )