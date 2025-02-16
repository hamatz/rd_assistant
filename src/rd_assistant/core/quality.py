from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from .memory import Requirement, ConversationMemory

@dataclass
class DetailedQualityScore:
    specificity: float       # 具体性
    measurability: float     # 測定可能性
    achievability: float     # 実現可能性
    relevance: float        # 関連性
    time_bound: float       # 期限の明確さ
    clarity: float          # 明確さ
    consistency: float      # 用語の一貫性
    vision_alignment: float # ビジョンとの整合性
    completeness: float     # 完全性
    total: float           # 総合スコア
    context_score: float   # 文脈スコア
    suggestions: List[str]  # 改善提案
    details: Dict[str, str] # 詳細な分析結果

class RequirementQualityChecker:
    # あいまいな表現のリスト
    AMBIGUOUS_TERMS = {
        'できれば', 'なるべく', 'たぶん', 'できるだけ', 'など', 'その他',
        '場合により', '必要に応じて', 'いくつかの', '多くの', '適切な',
        '柔軟な', '使いやすい', '高速な', '効率的な'
    }
    
    # 測定可能性を示す表現
    MEASURABLE_INDICATORS = {
        '秒', '分', '時間', '日', '週間', '月',
        '%', 'パーセント', '回', '件', '個',
        'MB', 'GB', 'TB', 'ms', 'fps'
    }

    TYPE_WEIGHTS = {
        "functional": {
            "specificity": 1.0,
            "measurability": 0.8,
            "achievability": 0.9,
            "relevance": 0.7,
            "time_bound": 0.6,
            "clarity": 1.0,
            "consistency": 0.8,
            "vision_alignment": 0.7,
            "completeness": 0.9,
            "context_score": 0.8
        },
        "non_functional": {
            "specificity": 0.9,
            "measurability": 1.0,
            "achievability": 0.8,
            "relevance": 0.8,
            "time_bound": 0.7,
            "clarity": 0.9,
            "consistency": 0.7,
            "vision_alignment": 0.8,
            "completeness": 0.8,
            "context_score": 0.9
        },
        "technical": {
            "specificity": 1.0,
            "measurability": 0.9,
            "achievability": 1.0,
            "relevance": 0.7,
            "time_bound": 0.8,
            "clarity": 0.9,
            "consistency": 1.0,
            "vision_alignment": 0.6,
            "completeness": 1.0,
            "context_score": 0.7
        },
        "business": {
            "specificity": 0.8,
            "measurability": 0.7,
            "achievability": 0.7,
            "relevance": 1.0,
            "time_bound": 0.9,
            "clarity": 0.8,
            "consistency": 0.7,
            "vision_alignment": 1.0,
            "completeness": 0.8,
            "context_score": 1.0
        }
    }

    async def analyze_requirement(self, req: Requirement, memory: ConversationMemory, llm_service) -> DetailedQualityScore:
        """要件の詳細な品質分析を実行"""
        base_scores = {
            "specificity": self._check_specificity(req.content),
            "measurability": self._check_measurability(req.content),
            "clarity": self._check_clarity(req.content),
            "consistency": self._check_term_consistency(req, memory),
            "completeness": self._check_completeness(req)
        }
        
        if memory.project_vision:
            vision_alignment = await self._check_vision_alignment(req, memory.project_vision, llm_service)
            base_scores["vision_alignment"] = vision_alignment

        llm_scores = await self._analyze_with_llm(req, memory, llm_service)
        scores = {**base_scores, **llm_scores}
        
        weights = self.TYPE_WEIGHTS.get(req.type, self.TYPE_WEIGHTS["functional"])
        weighted_scores = {
            k: v * weights[k] for k, v in scores.items() if k in weights
        }
        
        total = sum(weighted_scores.values()) / sum(weights.values())
        
        details = self._generate_detailed_analysis(req, scores, memory)

        suggestions = await self._generate_enhanced_suggestions(req, scores, memory, llm_service)

        return DetailedQualityScore(
            **scores,
            total=total,
            suggestions=suggestions,
            details=details
        )

    def _check_specificity(self, content: str) -> float:
        """要件の具体性をチェック"""
        # 文字数による基本スコア（短すぎず、長すぎない）
        length = len(content)
        length_score = min(1.0, max(0.0, length / 100)) if length < 100 else min(1.0, 200 / length)
        
        # 具体的な名詞や動詞の使用
        words = set(content.split())
        specific_terms_score = len(words) / 20  # 使用される単語の多様性
        
        return (length_score + specific_terms_score) / 2

    def _check_measurability(self, content: str) -> float:
        """測定可能性をチェック"""
        # 数値や単位の存在をチェック
        has_numbers = any(char.isdigit() for char in content)
        has_units = any(unit in content for unit in self.MEASURABLE_INDICATORS)
        
        # 定量的な表現の検出
        score = 0.0
        if has_numbers:
            score += 0.5
        if has_units:
            score += 0.5
            
        return min(1.0, score)

    def _check_clarity(self, content: str) -> float:
        """明確さ（あいまい表現の少なさ）をチェック"""
        words = content.split()
        ambiguous_count = sum(1 for word in words if word in self.AMBIGUOUS_TERMS)
        
        # あいまい表現が多いほどスコアが低くなる
        return max(0.0, min(1.0, 1.0 - (ambiguous_count / len(words))))

    async def _analyze_with_llm(self, req: Requirement, memory: ConversationMemory, llm_service) -> Dict[str, float]:
        """LLMを使用した高度な分析"""
        prompt = f"""
    以下の要件について、SMART基準に基づいて分析し、JSONフォーマットで回答してください：

    要件：{req.content}
    種類：{req.type}
    理由：{req.rationale}

    プロジェクト概要：
    {memory.project_description}

    以下の観点で0.0から1.0のスコアを付けて評価し、JSON形式で返してください：
    1. Achievable（実現可能性）: 技術的および組織的に実現可能か
    2. Relevant（関連性）: プロジェクトの目標に適切に関連しているか
    3. Time-bound（期限）: 時間的な制約や期限が明確か
    4. Context（文脈適合性）: プロジェクトの文脈に適切に沿っているか

    以下のJSONフォーマットで回答してください：
    {{
        "achievability": 0.0-1.0,
        "relevance": 0.0-1.0,
        "time_bound": 0.0-1.0,
        "context_score": 0.0-1.0,
        "reasoning": "スコアの理由の説明"
    }}
    """
        try:
            response = await llm_service.generate_response(prompt)
            return {
                "achievability": float(response.get("achievability", 0.5)),
                "relevance": float(response.get("relevance", 0.5)),
                "time_bound": float(response.get("time_bound", 0.5)),
                "context_score": float(response.get("context_score", 0.5))
            }
        except Exception as e:
            print(f"LLM分析中にエラーが発生しました: {str(e)}")
            return {
                "achievability": 0.5,
                "relevance": 0.5,
                "time_bound": 0.5,
                "context_score": 0.5
            }
    
    def _check_term_consistency(self, req: Requirement, memory: ConversationMemory) -> float:
        """用語の一貫性をチェック"""
        # 全要件から使用されている用語を収集
        all_terms = set()
        term_usage = {}
        
        for existing_req in memory.requirements:
            terms = self._extract_key_terms(existing_req.content)
            all_terms.update(terms)
            for term in terms:
                term_usage[term] = term_usage.get(term, 0) + 1
        
        # 現在の要件の用語をチェック
        current_terms = self._extract_key_terms(req.content)
        consistent_terms = sum(1 for term in current_terms if term_usage.get(term, 0) > 1)
        
        if not current_terms:
            return 0.5
        
        return consistent_terms / len(current_terms)

    def _generate_suggestions(self, req: Requirement, scores: Dict[str, float]) -> List[str]:
        """スコアに基づいて改善提案を生成"""
        suggestions = []
        
        # 具体性に関する提案
        if scores["specificity"] < 0.6:
            suggestions.append("より具体的な表現を使用してください")
        
        # 測定可能性に関する提案
        if scores["measurability"] < 0.6:
            suggestions.append("数値目標や測定可能な基準を含めることを検討してください")
        
        # あいまい表現に関する提案
        ambiguous_terms = [word for word in req.content.split() 
                          if word in self.AMBIGUOUS_TERMS]
        if ambiguous_terms:
            suggestions.append(
                f"以下のあいまいな表現をより具体的にすることを検討: {', '.join(ambiguous_terms)}")
        
        # 時間的制約に関する提案
        if scores["time_bound"] < 0.6:
            suggestions.append("実装や達成の期限を明確にすることを検討してください")
        
        return suggestions
    
    def _extract_key_terms(self, content: str) -> Set[str]:
        """重要な用語を抽出"""
        # 簡易的な実装。実際にはより高度な自然言語処理が必要かも
        words = content.split()
        # 一般的な助詞や助動詞を除外
        stop_words = {'は', 'を', 'が', 'の', 'に', 'へ', 'で', 'や', 'と', 'する', 'できる'}
        return {w for w in words if w not in stop_words and len(w) > 1}

    async def _check_vision_alignment(self, req: Requirement, vision, llm_service) -> float:
        """ビジョンとの整合性をチェック"""
        prompt = f"""
    プロジェクトビジョンと要件の整合性を分析し、JSONフォーマットで回答してください。

    プロジェクトビジョン：
    目標：{', '.join(vision.goals)}
    成功基準：{', '.join(vision.success_criteria)}
    対象ユーザー：{', '.join(vision.target_users)}

    要件：
    {req.content}
    種類：{req.type}
    理由：{req.rationale}

    以下のJSONフォーマットで回答してください：
    {{
        "alignment_score": 0.0-1.0,
        "reasoning": "スコアの理由"
    }}
    """
        try:
            response = await llm_service.generate_response(prompt)
            return float(response.get("alignment_score", 0.5))
        except Exception as e:
            print(f"ビジョン整合性チェック中にエラー: {str(e)}")
            return 0.5
        
    def _check_completeness(self, req: Requirement) -> float:
        """要件の完全性をチェック"""
        score = 0.0

        if req.content.strip():
            score += 0.4
        if req.rationale.strip():
            score += 0.3
        if not req.implicit:
            score += 0.2
        
        if req.metadata:
            score += 0.1
            
        return min(1.0, score)

    def _generate_detailed_analysis(self, req: Requirement, scores: Dict[str, float], memory: ConversationMemory) -> Dict[str, str]:
        """詳細な分析結果を生成"""
        details = {}
        
        # 具体性の分析
        if scores["specificity"] < 0.7:
            ambiguous_parts = []
            if len(req.content) < 50:
                ambiguous_parts.append("要件の記述が短すぎます")
            if not any(char.isdigit() for char in req.content):
                ambiguous_parts.append("数値による具体的な基準が含まれていません")
            if any(term in req.content for term in self.AMBIGUOUS_TERMS):
                ambiguous_terms = [term for term in self.AMBIGUOUS_TERMS if term in req.content]
                ambiguous_parts.append(f"あいまいな表現が含まれています: {', '.join(ambiguous_terms)}")
            details["specificity"] = "、".join(ambiguous_parts)

        # 測定可能性の分析
        if scores["measurability"] < 0.7:
            measurability_issues = []
            if not any(unit in req.content for unit in self.MEASURABLE_INDICATORS):
                measurability_issues.append("測定可能な指標が含まれていません")
            if not any(char.isdigit() for char in req.content):
                measurability_issues.append("数値目標が設定されていません")
            if measurability_issues:
                details["measurability"] = "、".join(measurability_issues)

        # 用語の一貫性分析
        terms = self._extract_key_terms(req.content)
        all_terms = self._get_all_terms(memory)
        term_issues = []
        
        # 類似した用語のチェック
        inconsistent_terms = []
        for term in terms:
            similar_terms = [
                other_term for other_term in all_terms
                if other_term != term and self._are_terms_similar(term, other_term)
            ]
            if similar_terms:
                inconsistent_terms.append(f"{term}（類似: {', '.join(similar_terms)}）")
        
        if inconsistent_terms:
            term_issues.append(f"類似した用語が異なる表現で使用されています: {', '.join(inconsistent_terms)}")
        
        # 頻出用語との整合性チェック
        common_terms = self._get_common_terms(memory)
        missing_common_terms = [
            term for term, count in common_terms.items()
            if count >= 3 and term not in terms and any(self._are_terms_similar(term, t) for t in terms)
        ]
        if missing_common_terms:
            term_issues.append(f"一般的に使用されている用語との不一致: {', '.join(missing_common_terms)}")
        
        if term_issues:
            details["term_consistency"] = "。".join(term_issues)

        # 完全性の分析
        completeness_issues = []
        if not req.rationale:
            completeness_issues.append("要件の背景や理由が記述されていません")
        if not req.metadata:
            completeness_issues.append("追加のメタデータが設定されていません")
        if 'priority' not in req.metadata:
            completeness_issues.append("優先度が設定されていません")
        if completeness_issues:
            details["completeness"] = "、".join(completeness_issues)

        # 要件タイプ固有の分析
        type_specific_issues = []
        if req.type == "functional":
            if not any(word in req.content.lower() for word in ["する", "できる", "実行", "表示", "保存"]):
                type_specific_issues.append("機能的な動作が明確に記述されていません")
        elif req.type == "non_functional":
            if not any(word in req.content.lower() for word in ["性能", "セキュリティ", "可用性", "信頼性"]):
                type_specific_issues.append("非機能要件として特徴的な品質特性が明確でありません")
        elif req.type == "technical":
            if not any(word in req.content.lower() for word in ["技術", "システム", "アーキテクチャ", "実装"]):
                type_specific_issues.append("技術的な詳細や制約が明確でありません")
        
        if type_specific_issues:
            details["type_specific"] = "、".join(type_specific_issues)

        # 依存関係の分析
        dependencies = self._analyze_dependencies(req, memory)
        if dependencies["implicit"]:
            details["dependencies"] = f"暗黙的な依存関係が検出されました: {', '.join(dependencies['implicit'])}"
        
        # 重複や矛盾の検出
        duplicates = self._find_similar_requirements(req, memory)
        if duplicates:
            details["duplication"] = f"類似した要件が存在します: {', '.join(duplicates)}"

        return details

    def _get_all_terms(self, memory: ConversationMemory) -> Set[str]:
        """全要件から用語を収集"""
        terms = set()
        for req in memory.requirements:
            terms.update(self._extract_key_terms(req.content))
        return terms

    def _get_common_terms(self, memory: ConversationMemory) -> Dict[str, int]:
        """頻出用語を収集"""
        term_counts = {}
        for req in memory.requirements:
            for term in self._extract_key_terms(req.content):
                term_counts[term] = term_counts.get(term, 0) + 1
        return term_counts

    def _are_terms_similar(self, term1: str, term2: str) -> bool:
        """用語の類似性をチェック"""
        # 完全一致は除外
        if term1 == term2:
            return False
        
        # 一方が他方に含まれる場合
        if term1 in term2 or term2 in term1:
            return True
        
        # 編集距離による類似度チェック
        if len(term1) > 3 and len(term2) > 3:
            distance = self._levenshtein_distance(term1, term2)
            max_length = max(len(term1), len(term2))
            similarity = 1 - (distance / max_length)
            return similarity > 0.7
        
        return False

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """編集距離を計算"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _analyze_dependencies(self, req: Requirement, memory: ConversationMemory) -> Dict[str, List[str]]:
        """要件の依存関係を分析"""
        explicit = []
        implicit = []
        
        # 明示的な依存関係（メタデータに記録されているもの）
        if 'dependencies' in req.metadata:
            explicit.extend(req.metadata['dependencies'])
        
        # 暗黙的な依存関係の検出
        content_lower = req.content.lower()
        for other_req in memory.requirements:
            if other_req == req:
                continue
                
            # 他の要件への参照を示唆する表現を検出
            reference_terms = ['による', 'を用いて', 'を使用', 'に基づく', 'と連携']
            other_terms = self._extract_key_terms(other_req.content)
            
            for term in other_terms:
                if term in content_lower and any(ref in content_lower for ref in reference_terms):
                    implicit.append(other_req.content)
                    break
        
        return {
            "explicit": explicit,
            "implicit": implicit
        }

    def _find_similar_requirements(self, req: Requirement, memory: ConversationMemory) -> List[str]:
        """類似した要件を検出"""
        similar_reqs = []
        req_terms = self._extract_key_terms(req.content)
        
        for other_req in memory.requirements:
            if other_req == req:
                continue
                
            other_terms = self._extract_key_terms(other_req.content)
            common_terms = req_terms & other_terms
            
            # 類似度の計算
            similarity = len(common_terms) / max(len(req_terms), len(other_terms))
            if similarity > 0.5:  # 50%以上の用語が共通する場合
                similar_reqs.append(other_req.content)
        
        return similar_reqs
    
    async def _generate_enhanced_suggestions(self, req: Requirement, scores: Dict[str, float], memory: ConversationMemory, llm_service) -> List[str]:
        """より詳細な改善提案を生成"""
        suggestions = []
        
        # スコアベースの提案
        for metric, score in scores.items():
            if score < 0.6:
                suggestions.extend(self._get_metric_based_suggestions(metric))
        
        # LLMを使用した文脈を考慮した提案
        context_suggestions = await self._get_context_aware_suggestions(req, memory, llm_service)
        suggestions.extend(context_suggestions)
        
        return suggestions

    def _get_metric_based_suggestions(self, metric: str) -> List[str]:
        """メトリクスに基づく改善提案"""
        suggestion_map = {
            "specificity": ["具体的な数値目標や条件を追加することを検討してください"],
            "measurability": ["測定可能な成功基準を含めることを検討してください"],
            "clarity": ["あいまいな表現を具体的な表現に置き換えることを検討してください"],
            "consistency": ["用語の使用を統一することを検討してください"],
            "completeness": ["要件の背景や理由をより詳細に記述することを検討してください"],
            "vision_alignment": ["プロジェクトの目標との関連性をより明確にすることを検討してください"]
        }
        return suggestion_map.get(metric, [])
    
    async def _get_context_aware_suggestions(self, req: Requirement, memory: ConversationMemory, llm_service) -> List[str]:
        """文脈を考慮した改善提案を生成"""
        prompt = f"""
    プロジェクトの文脈を考慮して、以下の要件に対する具体的な改善提案を生成し、JSONフォーマットで回答してください。

    プロジェクト情報：
    - 名称: {memory.project_name}
    - 概要: {memory.project_description}

    ビジョン情報：
    {self._format_vision_info(memory.project_vision) if memory.project_vision else "未設定"}

    対象要件：
    - 内容: {req.content}
    - 種類: {req.type}
    - 理由: {req.rationale}

    関連する要件：
    {self._format_related_requirements(req, memory)}

    以下のJSONフォーマットで回答してください：
    {{
        "suggestions": [
            {{
                "point": "改善ポイント",
                "suggestion": "具体的な改善提案",
                "reason": "提案の理由",
                "expected_impact": "期待される効果"
            }}
        ]
    }}
    """
        try:
            response = await llm_service.generate_response(prompt)
            suggestions = []
            
            if "suggestions" in response:
                for item in response["suggestions"]:
                    suggestion = f"{item['point']}: {item['suggestion']}"
                    if 'reason' in item:
                        suggestion += f"\n  理由: {item['reason']}"
                    if 'expected_impact' in item:
                        suggestion += f"\n  効果: {item['expected_impact']}"
                    suggestions.append(suggestion)
            
            return suggestions
        except Exception as e:
            print(f"改善提案生成中にエラー: {str(e)}")
            return []

    def _format_vision_info(self, vision) -> str:
        """ビジョン情報をフォーマット"""
        if not vision:
            return "ビジョン情報なし"
            
        lines = []
        if vision.goals:
            lines.append("目標:")
            lines.extend(f"- {goal}" for goal in vision.goals)
        
        if vision.success_criteria:
            lines.append("\n成功基準:")
            lines.extend(f"- {criteria}" for criteria in vision.success_criteria)
        
        if vision.target_users:
            lines.append("\n対象ユーザー:")
            lines.extend(f"- {user}" for user in vision.target_users)
        
        return "\n".join(lines)

    def _format_related_requirements(self, req: Requirement, memory: ConversationMemory) -> str:
        """関連する要件の情報をフォーマット"""
        # 同じタイプの要件を抽出
        same_type_reqs = [r for r in memory.requirements if r.type == req.type and r != req]
        
        # 依存関係のある要件を抽出
        dependent_reqs = []
        if 'dependencies' in req.metadata:
            dependent_reqs = [r for r in memory.requirements 
                            if r.content in req.metadata['dependencies']]
        
        lines = []
        
        if same_type_reqs:
            lines.append(f"\n同じ種類の要件:")
            lines.extend(f"- {r.content}" for r in same_type_reqs[:3])  # 最大3件まで
        
        if dependent_reqs:
            lines.append(f"\n依存関係のある要件:")
            lines.extend(f"- {r.content}" for r in dependent_reqs)
        
        return "\n".join(lines) if lines else "関連する要件なし"