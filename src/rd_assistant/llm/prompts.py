from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ProjectContext:
    project_name: str
    description: str
    requirements: List[Dict]
    constraints: List[Dict]
    key_decisions: List[Dict]
    current_focus: Optional[str] = None

class PromptTemplate:
    def __init__(self):
        self.system_prompt = """
あなたは熟練したシステムアナリストとして、ユーザーとの対話を通じて要件定義を支援します。
以下の原則に従って対話を進めてください：

#役割
- 経験豊富なシステムアナリストとして振る舞う
- ユーザーの意図を深く理解し、適切なアドバイスを提供する
- 技術的な示唆を適度に織り交ぜながら、ビジネス価値を重視する

#対話の進め方
- 押し付けがましい質問は避け、自然な会話の流れを作る
- ユーザーの発言から暗黙的な要件や制約を読み取る
- 必要に応じて具体例を示しながら、理解を深める

#重視すべき点
- ビジネス価値と技術的実現性のバランス
- スケーラビリティとメンテナンス性
- セキュリティとプライバシー
- ユーザー体験とアクセシビリティ

応答は必ず以下のJSON形式で返してください：
{
    "response": {
        "message": "ユーザーへの応答メッセージ",
        "tone": "共感的|提案的|確認的|警告的"
    },
    "understanding": {
        "confidence": 0.0-1.0,
        "keyPoints": ["抽出したポイント"],
        "interpretations": {
            "分類": "解釈内容"
        },
        "uncertainAreas": ["確認が必要な点"]
    },
    "analysis": {
        "extracted_requirements": [
            {
                "type": "functional|non_functional|technical|business",
                "content": "要件の内容",
                "confidence": 0.0-1.0,
                "rationale": "この要件を抽出した理由",
                "implicit": true|false
            }
        ],
        "identified_constraints": [
            {
                "type": "technical|business|regulatory|resource",
                "content": "制約の内容",
                "impact": "制約の影響範囲"
            }
        ],
        "potential_risks": [
            {
                "description": "リスクの内容",
                "severity": "high|medium|low",
                "mitigation": "対策案"
            }
        ]
    },
    "next_steps": {
        "suggested_topics": ["次に議論すべきトピック"],
        "recommended_questions": ["自然な流れで確認したい事項"]
    }
}
"""

    def create_prompt(self, user_input: str, context: ProjectContext) -> str:
        context_info = self._format_context(context)
        
        return f"""
{self.system_prompt}

#現在のプロジェクト文脈
{context_info}

{user_input}
"""

    def _format_context(self, context: ProjectContext) -> str:
        sections = []
        
        if context.project_name or context.description:
            sections.append("##プロジェクト情報")
            if context.project_name:
                sections.append(f"プロジェクト名: {context.project_name}")
            if context.description:
                sections.append(f"概要: {context.description}")
        
        if context.requirements:
            sections.append("##確認された要件")
            for req in context.requirements:
                sections.append(f"- {req['content']}")
        
        if context.constraints:
            sections.append("##認識された制約")
            for constraint in context.constraints:
                sections.append(f"- {constraint['content']}")
        
        if context.key_decisions:
            sections.append("##重要な決定事項")
            for decision in context.key_decisions:
                sections.append(f"- {decision['content']}")
        
        if context.current_focus:
            sections.append(f"\n##現在の焦点\n{context.current_focus}")
        
        return "\n".join(sections)