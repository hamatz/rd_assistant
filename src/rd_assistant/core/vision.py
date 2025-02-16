from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ProjectVision:
    goals: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    target_users: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    priorities: Dict[str, str] = field(default_factory=dict)  # 機能 -> 優先度のマッピング

@dataclass
class FeaturePriority:
    feature: str
    priority: str  # must_have, should_have, could_have, won't_have
    rationale: str
    dependencies: List[str] = field(default_factory=list)

class VisionManager:
    """プロジェクトのビジョンとスコープを管理するクラス"""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def extract_vision_from_conversation(self, conversation: str) -> ProjectVision:
        """会話からプロジェクトビジョンを抽出"""
        prompt = f"""
以下の会話からプロジェクトのビジョンと目標を分析してください。
プロジェクトの成功とスコープを明確にするため、できるだけ具体的な内容を抽出してください。

会話内容:
{conversation}

以下の点に特に注目して分析し、JSONとして回答してください：
1. 目標は定量的な指標を含めて具体的に
2. 成功基準は測定可能な形で
3. 対象ユーザーは具体的な属性や特徴を含めて
4. 制約事項は技術面、コスト面、時間面など多角的に
5. 現時点で重視する要素は具体的な理由とともに

{{
    "goals": [
        "定量的な指標を含む具体的な目標"
    ],
    "success_criteria": [
        "測定可能な成功基準"
    ],
    "target_users": [
        "具体的な属性を含むユーザー定義"
    ],
    "constraints": [
        "技術/コスト/時間などの制約"
    ],
    "key_priorities": [
        {{
            "aspect": "重視する要素（例：使いやすさ、セキュリティ、パフォーマンスなど）",
            "reason": "それを重視する理由",
            "impact": "その要素が与える影響"
        }}
    ]
}}
"""
        try:
            response = await self.llm_service.generate_response(prompt)
            vision = ProjectVision(
                goals=response.get("goals", []),
                success_criteria=response.get("success_criteria", []),
                target_users=response.get("target_users", []),
                constraints=response.get("constraints", [])
            )
            
            if "key_priorities" in response:
                vision.priorities = {
                    p["aspect"]: {
                        "reason": p["reason"],
                        "impact": p["impact"]
                    }
                    for p in response["key_priorities"]
                }
            
            return vision
        except Exception as e:
            print(f"❌ ビジョンの抽出中にエラーが発生しました: {str(e)}")
            return ProjectVision()


    def _format_list(self, items: List[str]) -> str:
        """リストを箇条書きテキストに変換"""
        return "\n".join(f"- {item}" for item in items)

    def format_vision_summary(self, vision: ProjectVision) -> str:
        """ビジョンの要約を生成"""
        lines = ["📋 プロジェクトビジョン"]
        
        if vision.goals:
            lines.extend(["\n🎯 目標："] + [f"  ・{goal}" for goal in vision.goals])
        
        if vision.success_criteria:
            lines.extend(["\n✨ 成功基準："] + [f"  ・{criteria}" for criteria in vision.success_criteria])
        
        if vision.target_users:
            lines.extend(["\n👥 対象ユーザー："] + [f"  ・{user}" for user in vision.target_users])
        
        if vision.constraints:
            lines.extend(["\n⚠️ 制約事項："] + [f"  ・{constraint}" for constraint in vision.constraints])
        
        if vision.priorities:
            lines.extend(["\n🎖️ 重点項目："])
            for aspect, details in vision.priorities.items():
                lines.append(f"  ・{aspect}")
                lines.append(f"    理由: {details['reason']}")
                lines.append(f"    影響: {details['impact']}")
        
        return "\n".join(lines)

    async def get_feature_priority(self, feature: str, vision: ProjectVision) -> Dict:
        """個別の機能の優先度を分析"""
        prompt = f"""
    以下の機能の優先度を、プロジェクトのビジョンと目標に基づいて分析してください：

    機能：{feature}

    プロジェクトの目標：
    {self._format_list(vision.goals)}

    成功基準：
    {self._format_list(vision.success_criteria)}

    以下の質問に答えてJSONとして回答してください：
    1. この機能は目標達成に必須ですか？
    2. この機能がないと、どのような問題が発生しますか？
    3. この機能の実装を後回しにした場合のリスクは何ですか？

    {{
        "analysis": {{
            "necessity_level": "この機能がないと目標達成が困難|この機能があると目標達成が容易|この機能は目標達成に直接影響しない",
            "impact": "この機能がない場合の影響",
            "delay_risk": "実装を後回しにした場合のリスク",
            "suggested_priority": "must_have|should_have|could_have|won't_have",
            "rationale": "優先度の判断理由"
        }}
    }}
    """
        try:
            response = await self.llm_service.generate_response(prompt)
            return response.get("analysis", {})
        except Exception as e:
            print(f"❌ 優先度分析でエラーが発生しました: {str(e)}")
            return {}

    def format_priority_summary(self, priorities: List[FeaturePriority]) -> str:
        """優先順位の要約を生成"""
        lines = ["📊 機能の優先順位"]
        
        priority_groups = {
            "must_have": "🔴 Must Have（必須）",
            "should_have": "🟡 Should Have（重要）",
            "could_have": "🟢 Could Have（あると良い）",
            "won't_have": "⚪ Won't Have（対象外）"
        }
        
        for priority_key, priority_label in priority_groups.items():
            features = [p for p in priorities if p.priority == priority_key]
            if features:
                lines.append(f"\n{priority_label}:")
                for feature in features:
                    lines.append(f"  ・{feature.feature}")
                    lines.append(f"    理由: {feature.rationale}")
                    if feature.dependencies:
                        lines.append(f"    依存: {', '.join(feature.dependencies)}")
        
        return "\n".join(lines)