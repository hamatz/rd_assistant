from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

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
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.history: List[UnderstandingStatus] = []
        
    def add_status(self, status: UnderstandingStatus):
        """新しい理解状況を追加"""
        self.history.append(status)
        self._update_markdown()
    
    def _update_markdown(self):
        """理解状況のMarkdownを更新"""
        content = ["# 要件定義支援AIの理解状況\n"]
        content.append(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if self.history:
            latest = self.history[-1]
            # 現在の理解度
            content.append("## 現在の理解度")
            confidence_bar = "█" * int(latest.confidence * 20)
            content.append(f"[{confidence_bar:<20}] {latest.confidence*100:.1f}%\n")
            
            # 最新の理解内容
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
            
            # 対話履歴
            content.append("\n## 対話履歴")
            for status in reversed(self.history):
                content.append(f"\n### {status.timestamp.strftime('%H:%M:%S')}")
                content.append(f"**ユーザー**: {status.user_input}")
                content.append(f"\n**AI**: {status.ai_response}")
                content.append("\n---")
        
        # ファイルに保存
        understanding_file = self.output_dir / "understanding.md"
        with open(understanding_file, "w", encoding="utf-8") as f:
            f.write("\n".join(content))