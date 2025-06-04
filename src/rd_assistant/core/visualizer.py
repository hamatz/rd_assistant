from typing import List, Dict
from .memory import ConversationMemory, Requirement

class RequirementsVisualizer:
    def generate_text_tree(self, memory: ConversationMemory) -> str:
        """要件をツリー形式のテキストで表示"""
        grouped_reqs = self._group_requirements(memory.requirements)
        
        lines = []
        lines.append(f"📋 {memory.project_name or 'プロジェクト要件'}")
        lines.append("")
        
        for req_type, reqs in grouped_reqs.items():
            type_name = self._get_requirement_type_name(req_type)
            lines.append(f"┌─ {type_name}")
            
            for req in reqs:
                lines.append(f"├── 📄 {req.content}")
                
                if req.rationale:
                    lines.append(f"│    └─ 💡 {req.rationale}")
                
                if req.confidence < 1.0:
                    confidence = f"{req.confidence * 100:.1f}%"
                    lines.append(f"│    └─ ⚖️ 確信度: {confidence}")
            
            lines.append("│")
        
        return "\n".join(lines)

    def generate_text_flow(self, memory: ConversationMemory) -> str:
        """要件の関係性をテキストで表示"""
        lines = []
        lines.append("🔄 要件の関係性")
        lines.append("")

        type_symbols = {
            "functional": "⚙️",
            "non_functional": "🔧",
            "technical": "💻",
            "business": "💼"
        }
        
        for i, req1 in enumerate(memory.requirements):
            symbol = type_symbols.get(req1.type, "📄")
            lines.append(f"{symbol} {req1.content}")
            
            related = []
            for j, req2 in enumerate(memory.requirements):
                if i != j and self._are_requirements_related(req1, req2):
                    related.append(f"  └─→ {type_symbols.get(req2.type, '📄')} {req2.content}")
            
            if related:
                lines.extend(related)
            lines.append("")
        
        return "\n".join(lines)

    def _group_requirements(self, requirements: List[Requirement]) -> Dict[str, List[Requirement]]:
        """要件をタイプごとにグループ化"""
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
    
    def generate_mindmap(self, memory: ConversationMemory) -> str:
        """要件のマインドマップを生成"""
        grouped_reqs = self._group_requirements(memory.requirements)
        
        lines = ["mindmap"]
        lines.append(f"  {memory.project_name or 'プロジェクト要件'}")
        
        for req_type, reqs in grouped_reqs.items():
            type_name = self._get_requirement_type_name(req_type)
            lines.append(f"    {type_name}")
            
            for req in reqs:
                content = self._truncate_text(req.content, 40)
                lines.append(f"      {content}")
                if req.rationale:
                    rationale = self._truncate_text(req.rationale, 30)
                    lines.append(f"        {rationale}")
        
        return "\n".join(lines)

    def generate_flowchart(self, memory: ConversationMemory) -> str:
        """要件間の関係性をフローチャートで表現"""
        lines = ["graph TD"]
        
        for i, req in enumerate(memory.requirements):
            node_id = f"R{i}"
            if req.type == "functional":
                lines.append(f"    {node_id}[{self._truncate_text(req.content, 30)}]")
            elif req.type == "non_functional":
                lines.append(f"    {node_id}{{{self._truncate_text(req.content, 30)}}}")
            else:
                lines.append(f"    {node_id}([{self._truncate_text(req.content, 30)}])")

        for i, req1 in enumerate(memory.requirements):
            for j, req2 in enumerate(memory.requirements):
                if i != j and self._are_requirements_related(req1, req2):
                    lines.append(f"    R{i} --> R{j}")
        
        return "\n".join(lines)

    def _get_requirement_type_name(self, req_type: str) -> str:
        """要件タイプの日本語名を取得"""
        return {
            "functional": "機能要件",
            "non_functional": "非機能要件",
            "technical": "技術要件",
            "business": "ビジネス要件"
        }.get(req_type, req_type)

    def _truncate_text(self, text: str, max_length: int) -> str:
        """テキストを指定の長さに切り詰め"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."

    def _are_requirements_related(self, req1: Requirement, req2: Requirement) -> bool:
        """2つの要件が関連しているかを推定"""
        if req1.type == req2.type:
            return True
        
        words1 = set(req1.content.split())
        words2 = set(req2.content.split())
        common_words = words1 & words2
        return len(common_words) >= 2
