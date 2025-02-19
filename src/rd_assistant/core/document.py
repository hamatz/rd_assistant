from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import json
from .memory import ConversationMemory, Requirement, Constraint, Risk

class DocumentGenerator:
    def __init__(self, memory: ConversationMemory):
        self.memory = memory

    def generate_markdown(self) -> str:
        """メモリの内容からMarkdownドキュメントを生成"""
        sections = [
            self._generate_header(),
            self._generate_project_overview(),
            self._generate_vision_section(),
            self._generate_visualization_section(),
            self._generate_requirements_section(),
            self._generate_constraints_section(),
            self._generate_risks_section(),
            self._generate_decisions_section()
        ]
        
        return "\n\n".join(sections)

    def _generate_header(self) -> str:
        return f"""# 要件定義書

作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    def _generate_project_overview(self) -> str:
        return f"""## プロジェクト概要

### プロジェクト名
{self.memory.project_name or "未設定"}

### 概要
{self.memory.project_description or "未設定"}
"""

    def _generate_requirements_section(self) -> str:
        sections = ["## 要件定義"]
        
        # 要件を種類ごとにグループ化
        grouped_reqs = self._group_requirements(self.memory.requirements)
        
        for req_type, reqs in grouped_reqs.items():
            if reqs:
                sections.append(f"\n### {self._get_requirement_type_name(req_type)}")
                for req in reqs:
                    sections.append(self._format_requirement(req))
        
        return "\n".join(sections)

    def _group_requirements(self, requirements: List[Requirement]) -> Dict[str, List[Requirement]]:
        grouped = {
            "functional": [],
            "non_functional": [],
            "technical": [],
            "business": []
        }
        
        for req in requirements:
            if req.type in grouped:
                grouped[req.type].append(req)
        
        return grouped

    def _get_requirement_type_name(self, req_type: str) -> str:
        return {
            "functional": "機能要件",
            "non_functional": "非機能要件",
            "technical": "技術要件",
            "business": "ビジネス要件"
        }.get(req_type, req_type)

    def _format_requirement(self, req: Requirement) -> str:
        confidence_str = f"(確信度: {req.confidence * 100:.1f}%)" if req.confidence < 1.0 else ""
        implicit_str = "(暗黙的に抽出)" if req.implicit else ""
        
        return f"""#### {req.content}
{confidence_str} {implicit_str}

理由：{req.rationale}
"""

    def _generate_constraints_section(self) -> str:
        if not self.memory.constraints:
            return "## 制約条件\n\n特に制約条件は定義されていません。"
        
        sections = ["## 制約条件"]
        
        for constraint in self.memory.constraints:
            sections.append(f"""### {constraint.content}

- 種類: {constraint.type}
- 影響範囲: {constraint.impact}
""")
        
        return "\n".join(sections)

    def _generate_risks_section(self) -> str:
        if not self.memory.risks:
            return "## リスク\n\n特にリスクは検出されていません。"
        
        sections = ["## リスク"]
        
        for risk in self.memory.risks:
            sections.append(f"""### {risk.description}

- 深刻度: {risk.severity}
- 対策案: {risk.mitigation}
""")
        
        return "\n".join(sections)

    def _generate_decisions_section(self) -> str:
        if not self.memory.key_decisions:
            return "## 重要な決定事項\n\n特に重要な決定事項は記録されていません。"
        
        sections = ["## 重要な決定事項"]
        
        for decision in self.memory.key_decisions:
            sections.append(f"""### {decision['content']}

決定日時: {decision['created_at'].strftime('%Y-%m-%d %H:%M:%S')}
""")
        
        return "\n".join(sections)

    def save_document(self, output_dir: str = "outputs") -> str:
        """ドキュメントをファイルとして保存"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        project_name = self.memory.project_name.replace(" ", "_") if self.memory.project_name else "project"
        doc_filename = f"requirements_{project_name}_{timestamp}.md"
        
        document = self.generate_markdown()
        
        doc_path = output_path / doc_filename
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(document)
        
        history_filename = f"change_history_{project_name}_{timestamp}.md"
        history_path = output_path / history_filename
        
        with open(history_path, 'w', encoding='utf-8') as f:
            f.write(self.memory.history_manager.generate_history_markdown())
        
        return {
            "requirements": str(doc_path),
            "history": str(history_path)
        }
    
    def _generate_vision_section(self) -> str:
        """プロジェクトビジョンのセクションを生成"""
        if not self.memory.project_vision:
            return "## プロジェクトビジョン\n\nビジョンはまだ定義されていません。"
        
        vision = self.memory.project_vision
        
        sections = ["## プロジェクトビジョン"]
        
        if vision.goals:
            sections.append("\n### 目標")
            for goal in vision.goals:
                sections.append(f"- {goal}")
        
        if vision.success_criteria:
            sections.append("\n### 成功基準")
            for criteria in vision.success_criteria:
                sections.append(f"- {criteria}")
        
        if vision.target_users:
            sections.append("\n### 対象ユーザー")
            for user in vision.target_users:
                sections.append(f"- {user}")
        
        if self.memory.feature_priorities:
            sections.append("\n### 機能の優先順位")
            priority_groups = {
                "must_have": "Must Have（必須）",
                "should_have": "Should Have（重要）",
                "could_have": "Could Have（あると良い）",
                "won't_have": "Won't Have（対象外）"
            }
            
            for priority_key, priority_label in priority_groups.items():
                features = [p for p in self.memory.feature_priorities if p.priority == priority_key]
                if features:
                    sections.append(f"\n#### {priority_label}")
                    for feature in features:
                        sections.append(f"- {feature.feature}")
                        if feature.rationale:
                            sections.append(f"  - 理由: {feature.rationale}")
                        if feature.dependencies:
                            sections.append(f"  - 依存: {', '.join(feature.dependencies)}")
        
        return "\n".join(sections)
    
    def _generate_visualization_section(self) -> str:
        """要件の視覚化セクションを生成"""
        from .visualizer import RequirementsVisualizer
        visualizer = RequirementsVisualizer()
        
        sections = ["## 要件の視覚化"]
        
        sections.append("\n### 要件マップ")
        sections.append("以下のマインドマップは、要件の全体像と階層構造を示しています：")
        sections.append("\n```mermaid")
        sections.append(visualizer.generate_mindmap(self.memory))
        sections.append("```")
        
        sections.append("\n### 要件の関係性")
        sections.append("以下の図は、要件間の依存関係と関連性を示しています：")
        sections.append("\n```mermaid")
        sections.append(visualizer.generate_flowchart(self.memory))
        sections.append("```")
        
        if self.memory.feature_priorities:
            sections.append("\n### 優先順位マップ")
            sections.append("以下の図は、要件の優先順位と依存関係を示しています：")
            sections.append("\n```mermaid")
            sections.append(self._generate_priority_flowchart())
            sections.append("```")
        
        return "\n".join(sections)

    def _generate_priority_flowchart(self) -> str:
        """優先順位を考慮した階層型フローチャートを生成"""
        lines = ["graph TD"]
        
        # 優先度ごとのスタイル定義
        priority_styles = {
            "must_have": {
                "color": "#ff6b6b",
                "prefix": "🔴",
                "title": "Must Have（必須）"
            },
            "should_have": {
                "color": "#ffd93d",
                "prefix": "🟡",
                "title": "Should Have（重要）"
            },
            "could_have": {
                "color": "#6bff6b",
                "prefix": "🟢",
                "title": "Could Have（あると良い）"
            },
            "won't_have": {
                "color": "#d3d3d3",
                "prefix": "⚪",
                "title": "Won't Have（対象外）"
            }
        }
        
        # 優先度ごとにグループ化
        grouped_reqs = {
            "must_have": [],
            "should_have": [],
            "could_have": [],
            "won't_have": []
        }
        
        # 要件をグループに分類
        for i, req in enumerate(self.memory.requirements):
            priority = req.metadata.get('priority', 'undefined')
            if priority in grouped_reqs:
                grouped_reqs[priority].append((i, req))
        
        # サブグラフとして各優先度グループを生成
        for priority, style in priority_styles.items():
            reqs = grouped_reqs[priority]
            if reqs:
                lines.append(f"    subgraph {priority}_group[\"{style['title']}\"]")
                
                # グループ内の要件を追加
                for i, (idx, req) in enumerate(reqs):
                    node_id = f"R{idx}"
                    content = req.content if len(req.content) < 30 else req.content[:27] + "..."
                    lines.append(f"        {node_id}[\"{style['prefix']} {content}\"]")
                    lines.append(f"        style {node_id} fill:{style['color']}")
                
                lines.append("    end")
        
        # 依存関係の追加
        for priority in priority_styles.keys():
            for idx, req in grouped_reqs[priority]:
                if 'dependencies' in req.metadata:
                    for dep in req.metadata['dependencies']:
                        for other_idx, other_req in enumerate(self.memory.requirements):
                            if other_req.content == dep:
                                lines.append(f"    R{other_idx} --> R{idx}")
        
        # グラフの方向を上から下に設定
        lines.append("    %% 方向設定")
        lines.append("    direction TB")
        
        return "\n".join(lines)