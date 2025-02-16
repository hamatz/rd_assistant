from typing import Optional
from datetime import datetime
from .memory import Requirement

class RequirementsEditor:
    """要件の編集を管理するクラス"""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def edit_requirement(self, requirement: Requirement, edit_type: str, new_value: str) -> Optional[Requirement]:
        """要件の編集と検証"""
        try:
            # 編集内容の検証用プロンプト
            prompt = f"""
現在の要件を以下のように変更することの妥当性を評価し、必要に応じて改善提案をしてください：

現在の要件：
- 内容: {requirement.content}
- 種類: {requirement.type}
- 理由: {requirement.rationale}

変更点：
- 項目: {edit_type}
- 新しい値: {new_value}

以下の点を確認してください：
1. 変更後も要件として適切か
2. 他の要件との整合性は保たれているか
3. 表現は明確で具体的か
4. 必要に応じて改善提案を行う

以下の形式でJSONとして回答してください：
{{
    "evaluation": {{
        "is_valid": true|false,
        "reason": "妥当性の理由や問題点の説明",
        "suggestion": "改善提案（必要な場合）",
        "improved_value": "提案された改善後の値（必要な場合）"
    }}
}}
"""
            response = await self.llm_service.generate_response(prompt)
            
            if 'evaluation' in response:
                eval_data = response['evaluation']
                
                if eval_data.get('is_valid', False):
                    new_requirement = Requirement(
                        content=new_value if edit_type == 'content' else requirement.content,
                        type=new_value if edit_type == 'type' else requirement.type,
                        rationale=new_value if edit_type == 'rationale' else requirement.rationale,
                        confidence=requirement.confidence,
                        implicit=requirement.implicit,
                        created_at=requirement.created_at
                    )
                    return new_requirement
                else:
                    print(f"\n⚠️ 編集内容に問題があります：")
                    print(f"理由: {eval_data.get('reason', '不明')}")
                    if 'suggestion' in eval_data and eval_data['suggestion']:
                        print(f"提案: {eval_data['suggestion']}")
                    if 'improved_value' in eval_data and eval_data['improved_value']:
                        print(f"改善案: {eval_data['improved_value']}")
                        
                        print("\n改善案を採用しますか？")
                        return await self.edit_requirement(requirement, edit_type, eval_data['improved_value'])
                    
                    return None
            
            return None
            
        except Exception as e:
            print(f"❌ 要件の編集中にエラーが発生しました: {str(e)}")
            return None

    def format_requirement_for_display(self, index: int, req: Requirement) -> str:
        """要件を表示用にフォーマット"""
        return f"""
[{index + 1}] 要件:
    種類: {req.type}
    内容: {req.content}
    理由: {req.rationale}
    確信度: {req.confidence * 100:.1f}%
    作成日時: {req.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""