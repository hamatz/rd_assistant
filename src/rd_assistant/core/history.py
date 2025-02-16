from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ChangeRecord:
    timestamp: datetime
    action: str  # 'add', 'update', 'delete', 'review', 'organize'
    target_type: str  # 'requirement', 'vision', 'constraint', etc.
    target_id: str  # 要件のcontent等、対象を特定できる情報
    details: Dict[str, Any]  # 変更の詳細情報
    reason: Optional[str] = None  # 変更理由（あれば）

class ChangeHistoryManager:
    def __init__(self):
        self.history: List[ChangeRecord] = []
        self.start_time: datetime = datetime.now()

    def record_change(self, action: str, target_type: str, target_id: str, 
                     details: Dict[str, Any], reason: Optional[str] = None):
        """変更を記録"""
        record = ChangeRecord(
            timestamp=datetime.now(),
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            reason=reason
        )
        self.history.append(record)

    def get_changes_since(self, timestamp: datetime) -> List[ChangeRecord]:
        """指定時刻以降の変更を取得"""
        return [
            record for record in self.history
            if record.timestamp >= timestamp
        ]

    def generate_history_markdown(self) -> str:
        """変更履歴をMarkdown形式で生成"""
        if not self.history:
            return "# 変更履歴\n\n変更履歴はありません。"

        sections = ["# 変更履歴"]
        
        changes_by_date = {}
        for record in sorted(self.history, key=lambda x: x.timestamp):
            date_str = record.timestamp.strftime('%Y-%m-%d')
            if date_str not in changes_by_date:
                changes_by_date[date_str] = []
            changes_by_date[date_str].append(record)

        for date, changes in changes_by_date.items():
            sections.append(f"\n## {date}")
            
            for change in sorted(changes, key=lambda x: x.timestamp):
                time_str = change.timestamp.strftime('%H:%M:%S')
                
                emoji = {
                    'add': '➕',
                    'update': '✏️',
                    'delete': '❌',
                    'review': '👀',
                    'organize': '🔄'
                }.get(change.action, '📝')
                
                sections.append(f"\n### {time_str} {emoji} {self._format_action(change.action)}")
                sections.append(f"対象: {self._format_target_type(change.target_type)}")
                
                if change.target_id:
                    sections.append(f"内容: {change.target_id}")
                
                if change.details:
                    sections.append("\n変更詳細:")
                    sections.extend(self._format_change_details(change.details))
                
                if change.reason:
                    sections.append(f"\n理由: {change.reason}")

        return "\n".join(sections)

    def _format_action(self, action: str) -> str:
        """アクションを日本語に変換"""
        return {
            'add': '追加',
            'update': '更新',
            'delete': '削除',
            'review': 'レビュー',
            'organize': '再整理'
        }.get(action, action)

    def _format_target_type(self, target_type: str) -> str:
        """対象種別を日本語に変換"""
        return {
            'requirement': '要件',
            'vision': 'ビジョン',
            'constraint': '制約'
        }.get(target_type, target_type)

    def _format_change_details(self, details: Dict[str, Any]) -> List[str]:
        """変更詳細をフォーマット"""
        formatted = []
        
        if 'type' in details:
            formatted.append(f"- 種類: {details['type']}")
        if 'content' in details:
            formatted.append(f"- 内容: {details['content']}")
        if 'rationale' in details:
            formatted.append(f"- 理由: {details['rationale']}")
            
        if 'old_value' in details and 'new_value' in details:
            formatted.append(f"- 変更前: {details['old_value']}")
            formatted.append(f"- 変更後: {details['new_value']}")
            
        if 'review_score' in details:
            formatted.append(f"- 品質スコア: {details['review_score']:.2f}")
        if 'suggestions' in details:
            formatted.append("- 改善提案:")
            for suggestion in details['suggestions']:
                formatted.append(f"  - {suggestion}")
                
        return formatted

    def save_history(self, output_dir: str = "outputs") -> str:
        """変更履歴を保存"""
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"change_history_{timestamp}.md"
        
        history_md = self.generate_history_markdown()
        file_path = output_path / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(history_md)
        
        return str(file_path)