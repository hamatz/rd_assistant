from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from .memory import ConversationMemory

@dataclass
class UnderstandingStatus:
    timestamp: datetime
    confidence: float
    key_points: List[str]
    interpretations: Dict[str, str]
    uncertain_areas: List[str]
    user_input: str
    ai_response: str

class UnderstandingTracker:
    def __init__(self, memory: ConversationMemory,  output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.memory = memory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.history: List[UnderstandingStatus] = []
        self.understanding_file = self._get_understanding_file()
        
    def update_requirements(self):
        """要件一覧が変更された際に呼び出す"""
        self._update_markdown()

    def _get_understanding_file(self) -> Path:
        """プロジェクトごとの理解状況ファイルパスを生成"""
        safe_name = "".join(c for c in self.memory.project_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_').lower() or "unnamed_project"
        return self.output_dir / f"understanding_{safe_name}.md"

    def add_status(self, status: UnderstandingStatus):
        """新しい理解状況を追加"""
        self.history.append(status)
        self._update_markdown()
    
    def _update_markdown(self):
        """理解状況のMarkdownを更新"""
        content = ["# RD-Assistantの理解状況\n"]
        content.append(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        content.append("## 📋 現在の要件一覧")
        
        requirements = self.memory.requirements
        grouped_reqs = {
            "functional": [],
            "non_functional": [],
            "technical": [],
            "business": []
        }
        
        for req in requirements:
            if req.type in grouped_reqs:
                grouped_reqs[req.type].append(req)
        
        type_names = {
            "functional": "🔧 機能要件",
            "non_functional": "⚙️ 非機能要件",
            "technical": "💻 技術要件",
            "business": "💼 ビジネス要件"
        }
        
        for req_type, reqs in grouped_reqs.items():
            if reqs:
                content.append(f"\n### {type_names[req_type]}")
                for req in reqs:
                    priority = req.metadata.get('priority', '')
                    priority_emoji = {
                        'must_have': '🔴',
                        'should_have': '🟡',
                        'could_have': '🟢',
                        'won\'t_have': '⚪'
                    }.get(priority, '')
                    
                    content.append(f"\n#### {priority_emoji} {req.content}")
                    if req.rationale:
                        content.append(f"理由: {req.rationale}")
                    if 'review_score' in req.metadata:
                        score = req.metadata['review_score']
                        content.append(f"品質スコア: {score:.2f}")
        
        content.append("\n---\n") 
        
        if self.history:
            latest = self.history[-1]
            content.append("## 現在の理解度")
            confidence_bar = "█" * int(latest.confidence * 20)
            content.append(f"[{confidence_bar:<20}] {latest.confidence*100:.1f}%\n")

            content.append("## 最新の理解内容")
            content.append("\n### 抽出したキーポイント")
            for point in latest.key_points:
                content.append(f"- {point}")
            
            content.append("\n### 要件として解釈した内容")
            for category, interpretation in latest.interpretations.items():
                content.append(f"#### {category}")
                content.append(interpretation)
            
            if latest.uncertain_areas:
                content.append("\n### 確認が必要な点")
                for area in latest.uncertain_areas:
                    content.append(f"- ❓ {area}")
            
            content.append("\n## 📝 対話履歴")
            for status in reversed(self.history[-10:]):  # 最新10件のみ表示
                content.append(f"\n### {status.timestamp.strftime('%H:%M:%S')}")
                content.append(f"**ユーザー**: {status.user_input}")
                content.append(f"\n**AI**: {status.ai_response}")
                content.append("\n---")

        with open(self.understanding_file, "w", encoding="utf-8") as f:
            f.write("\n".join(content))