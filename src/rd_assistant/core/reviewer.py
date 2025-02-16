from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import re
from .memory import ConversationMemory, Requirement

@dataclass
class ReviewComment:
    role: str
    category: str
    content: str
    importance: str  # high, medium, low
    suggestion: str

@dataclass
class ReviewResult:
    comments: List[ReviewComment]
    overall_evaluation: str
    improvement_suggestions: List[Dict]
    discussion_summary: str
    discussion: List[Dict] = field(default_factory=list)

@dataclass
class DocumentChunk:
    content: str
    section_type: str
    section_name: str
    requirements_count: int

class DocumentProcessor:
    """要件定義書の分割と処理を管理するクラス"""
    
    def __init__(self, llm_config: 'LLMConfig'):
        # コンテキストウィンドウの25%をレスポンス用に確保
        self.max_chunk_size = int(llm_config.max_tokens * 0.75)

    async def process_document(self, document: str) -> List[DocumentChunk]:
        """文書を必要に応じて分割"""
        estimated_tokens = self.estimate_tokens(document)
        print(f"\n📊 推定トークン数: {estimated_tokens}")
        
        if estimated_tokens <= self.max_chunk_size:
            print("\n🔍 文書を一括で処理します...")
            return [DocumentChunk(
                content=document,
                section_type="complete",
                section_name="完全な文書",
                requirements_count=document.count('###')
            )]
        
        print(f"\n🔄 文書を分割して処理します...")
        print(f"   最大チャンクサイズ: {self.max_chunk_size}")
        return self._split_document(document)

    def _split_document(self, document: str) -> List[DocumentChunk]:
        """要件定義書を適切なサイズのチャンクに分割"""
        chunks = []
        current_section = ""
        current_content = []
        current_size = 0
        requirements_count = 0

        lines = document.split('\n')
        for line in lines:
            if line.startswith('# '):
                if current_content:
                    chunks.append(self._create_chunk(current_section, current_content, requirements_count))
                current_section = line
                current_content = [line]
                current_size = len(line)
                requirements_count = 0
            elif line.startswith('## '):
                if current_size > self.max_chunk_size:
                    chunks.append(self._create_chunk(current_section, current_content, requirements_count))
                    current_content = []
                    current_size = 0
                    requirements_count = 0
                current_section = line
                current_content.append(line)
                current_size += len(line)
            else:
                if '###' in line:
                    requirements_count += 1
                
                current_content.append(line)
                current_size += len(line)
                
                # チャンクサイズの制限を超えた場合
                if current_size > self.max_chunk_size:
                    chunks.append(self._create_chunk(current_section, current_content, requirements_count))
                    current_content = []
                    current_size = 0
                    requirements_count = 0

        if current_content:
            chunks.append(self._create_chunk(current_section, current_content, requirements_count))

        return chunks

    def _create_chunk(self, section: str, content: List[str], req_count: int) -> DocumentChunk:
        """チャンクオブジェクトを作成"""
        section_type = "header" if section.startswith("# ") else "section"
        section_name = section.strip("# ").strip()
        return DocumentChunk(
            content="\n".join(content),
            section_type=section_type,
            section_name=section_name,
            requirements_count=req_count
        )

    def estimate_tokens(self, text: str) -> int:
        """テキストのトークン数を概算"""
        # 文字数をベースにした簡易的な推定
        # 英語は平均4文字/トークン、日本語は2文字/トークン程度として計算
        jp_char_count = len(re.findall(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]', text))
        en_char_count = len(text) - jp_char_count
        
        return (jp_char_count // 2) + (en_char_count // 4)

class ReviewManager:
    """レビュープロセスを管理するクラス"""
    
    def __init__(self, llm_service, max_tokens: int = 4000):
        self.llm_service = llm_service
        self.max_tokens = max_tokens
        self.document_processor = DocumentProcessor(self.llm_service.config)

    async def process_document(self, document: str, memory: ConversationMemory) -> ReviewResult:
        """文書を分割して処理し、結果を統合"""
        chunks = self.document_processor.split_document(document)
        
        chunk_reviews = []
        
        print(f"\n📄 文書を {len(chunks)} 個のセクションに分割して処理します...")
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\n🔍 セクション {i}/{len(chunks)} を処理中: {chunk.section_name}")
            print(f"   要件数: {chunk.requirements_count}")
            
            review = await self._review_chunk(chunk, memory)
            chunk_reviews.append(review)
        
        return self._merge_reviews(chunk_reviews)

    async def _review_chunk(self, chunk: DocumentChunk, memory: ConversationMemory) -> Dict:
        """個別のチャンクをレビュー"""
        prompt = self._create_review_prompt(chunk, memory)
        
        try:
            response = await self.llm_service.generate_response(prompt)
            print(f"✅ {chunk.section_name} のレビューが完了")
            return response
        except Exception as e:
            print(f"⚠️ {chunk.section_name} のレビュー中にエラー: {str(e)}")
            return self._create_empty_review()

    def _create_review_prompt(self, chunk: DocumentChunk, memory: ConversationMemory) -> str:
        """チャンク用のレビュープロンプトを生成"""
        return f"""
このセクションの要件定義書をレビューしてください。

プロジェクト概要:
{memory.project_description}

セクション: {chunk.section_name}
内容:
{chunk.content}

以下の形式でJSONとして回答してください：
{{
    "comments": [
        {{
            "category": "レビューカテゴリ",
            "content": "レビューコメント",
            "importance": "high|medium|low",
            "suggestion": "改善提案"
        }}
    ]
}}
"""

    def _create_empty_review(self) -> Dict:
        """エラー時の空のレビュー結果を生成"""
        return {
            "comments": [],
            "section_status": "error"
        }

    def _merge_reviews(self, reviews: List[Dict]) -> ReviewResult:
        """複数のレビュー結果を統合"""
        all_comments = []
        for review in reviews:
            for comment_data in review.get("comments", []):
                try:
                    comment = ReviewComment(
                        role="統合レビュー",
                        category=comment_data["category"],
                        content=comment_data["content"],
                        importance=comment_data["importance"],
                        suggestion=comment_data["suggestion"]
                    )
                    all_comments.append(comment)
                except KeyError:
                    continue
        
        unique_comments = self._deduplicate_comments(all_comments)
        
        return ReviewResult(
            comments=unique_comments,
            overall_evaluation=self._generate_overall_evaluation(reviews),
            improvement_suggestions=self._merge_suggestions(reviews),
            discussion_summary=self._generate_merged_summary(reviews)
        )

    def _deduplicate_comments(self, comments: List[ReviewComment]) -> List[ReviewComment]:
        """重複するコメントを排除"""
        seen = set()
        unique = []
        
        for comment in comments:
            key = (comment.content, comment.category)
            if key not in seen:
                seen.add(key)
                unique.append(comment)
        
        importance_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(unique, key=lambda x: importance_order[x.importance])

    def _generate_overall_evaluation(self, reviews: List[Dict]) -> str:
        """全体評価を生成"""
        return "全セクションのレビューが完了しました。"

    def _merge_suggestions(self, reviews: List[Dict]) -> List[Dict]:
        """改善提案を統合"""
        all_suggestions = []
        for review in reviews:
            if "suggestions" in review:
                all_suggestions.extend(review["suggestions"])
        
        seen = set()
        unique_suggestions = []
        for suggestion in all_suggestions:
            key = (suggestion.get("area", ""), suggestion.get("suggestion", ""))
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions

    def _generate_merged_summary(self, reviews: List[Dict]) -> str:
        """統合された要約を生成"""
        return "各セクションのレビュー結果を統合しました。"

class RequirementsReviewer:
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.review_manager = ReviewManager(llm_service)
        self.reviewer_roles = [
            {
                "role": "技術アーキテクト",
                "focus": "技術的な実現可能性、スケーラビリティ、保守性"
            },
            {
                "role": "セキュリティ専門家",
                "focus": "セキュリティリスク、プライバシー、コンプライアンス"
            },
            {
                "role": "ユーザー体験デザイナー",
                "focus": "ユーザビリティ、アクセシビリティ、ユーザー満足度"
            },
            {
                "role": "ビジネスアナリスト",
                "focus": "ビジネス価値、市場適合性、ROI"
            },
            {
                "role": "プロジェクトマネージャー",
                "focus": "実現可能性、リソース要件、スケジュール"
            }
        ]

    async def review_requirements(self, memory: ConversationMemory, document: str) -> ReviewResult:
        """要件定義書のレビューを実行"""
        try:
            chunks = await self.review_manager.document_processor.process_document(document)
            
            if len(chunks) == 1:
                return await self._perform_single_review(document, memory)
            else:
                return await self._perform_chunked_review(chunks, memory)
                
        except Exception as e:
            print(f"\n❌ レビュー処理中にエラーが発生しました: {str(e)}")
            raise

    async def _generate_discussion(self, reviews: List[ReviewComment], document: str) -> Dict:
        """専門家間の討論を生成"""
        print("\n💭 専門家間の討論を生成中...")
        
        reviews_text = "\n".join([
            f"{review.role}のコメント:\n"
            f"- 分類: {review.category}\n"
            f"- 内容: {review.content}\n"
            f"- 提案: {review.suggestion}\n"
            for review in reviews
        ])

        prompt = f"""
    以下の要件定義書に対する各専門家のレビューを基に、建設的な討論を生成してください。
    異なる視点からの意見を考慮し、バランスの取れた評価と改善の方向性を示してください。

    レビューコメント:
    {reviews_text}

    要件定義書:
    {document}

    以下の形式でJSONとして回答してください：
    {{
        "discussion": [
            {{
                "speaker": "専門家の役割",
                "point": "議論のポイント",
                "response_to": "他の専門家の指摘への応答（該当する場合）"
            }}
        ],
        "summary": "討論の要約と主要な合意点",
        "evaluation": "要件定義書の総合評価"
    }}
    """
        try:
            response = await self.llm_service.generate_response(prompt)
            print("✅ 討論の生成が完了")
            return response
        except Exception as e:
            print(f"❌ 討論生成中にエラー: {str(e)}")
            return {
                "discussion": [],
                "summary": "討論の生成中にエラーが発生しました",
                "evaluation": "評価を完了できませんでした"
            }
        
    async def _generate_improvements(self, reviews: List[ReviewComment], discussion: Dict) -> Dict:
        """最終的な改善提案を生成"""
        print("\n💡 改善提案を生成中...")
        
        reviews_text = "\n".join([
            f"- {review.role}: {review.content} (重要度: {review.importance})"
            for review in reviews
        ])

        prompt = f"""
    以下のレビューと討論の結果を基に、具体的な改善提案をまとめてください。
    提案は実行可能で、優先順位が明確なものにしてください。

    レビューコメント:
    {reviews_text}

    討論サマリー:
    {discussion.get('summary', '討論情報なし')}

    以下の形式でJSONとして回答してください：
    {{
        "suggestions": [
            {{
                "priority": "high|medium|low",
                "area": "改善領域",
                "suggestion": "具体的な改善提案",
                "rationale": "提案の理由"
            }}
        ]
    }}
    """
        try:
            response = await self.llm_service.generate_response(prompt)
            print("✅ 改善提案の生成が完了")
            return response
        except Exception as e:
            print(f"❌ 改善提案生成中にエラー: {str(e)}")
            return {"suggestions": []}     

    async def _perform_single_review(self, document: str, memory: ConversationMemory) -> ReviewResult:
        """文書が小さい場合の単一レビュー処理"""
        reviews = []
        for role in self.reviewer_roles:
            review = await self._get_expert_review(role, document, memory)
            reviews.extend(review)

        discussion = await self._generate_discussion(reviews, document)

        improvements = await self._generate_improvements(reviews, discussion)

        return ReviewResult(
            comments=reviews,
            overall_evaluation=discussion.get("evaluation", "評価を完了できませんでした"),
            improvement_suggestions=improvements.get("suggestions", []),
            discussion_summary=discussion.get("summary", "討論のまとめを生成できませんでした"),
            discussion=discussion.get("discussion", [])
        )

    async def _perform_chunked_review(self, chunks: List[DocumentChunk], memory: ConversationMemory) -> ReviewResult:
        """分割された文書のレビューを実行"""
        chunk_reviews = []
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\n📄 セクション {i}/{len(chunks)} をレビュー中: {chunk.section_name}")
            review = await self._perform_single_review(chunk.content, memory)
            chunk_reviews.append(review)
        
        return self._merge_review_results(chunk_reviews)

    async def _get_expert_review(self, role: Dict, document: str, memory: ConversationMemory) -> List[ReviewComment]:
        """各専門家の役割でのレビューを取得"""
        print(f"\n👤 {role['role']}としてレビューを実行中...")
        
        vision_context = ""
        if memory.project_vision:
            vision = memory.project_vision
            vision_context = f"""
    プロジェクトのビジョン：
    - 目標: {', '.join(vision.goals)}
    - 成功基準: {', '.join(vision.success_criteria)}
    - 対象ユーザー: {', '.join(vision.target_users)}
    """
        
        prompt = f"""
    あなたは{role['role']}として、以下の要件定義書をレビューしてください。
    特に {role['focus']} の観点から評価を行ってください。

    {vision_context}
    プロジェクト概要:
    {memory.project_description}

    要件定義書:
    {document}

    以下の点を考慮してレビューを行ってください：
    1. 要件がプロジェクトの目標や成功基準と整合しているか
    2. 対象ユーザーのニーズを適切に満たしているか
    3. 設定された優先順位が妥当か
    4. あなたの専門分野からみた課題や改善点

    以下の形式でJSONとして回答してください：
    {{
        "comments": [
            {{
                "category": "レビューカテゴリ",
                "content": "レビューコメント",
                "importance": "high|medium|low",
                "suggestion": "改善提案"
            }}
        ]
    }}
    """
        try:
            response = await self.llm_service.generate_response(prompt)
            print(f"✅ {role['role']}のレビューが完了")
            
            comments = []
            for comment_data in response.get("comments", []):
                try:
                    comment = ReviewComment(
                        role=role["role"],
                        category=comment_data["category"],
                        content=comment_data["content"],
                        importance=comment_data["importance"],
                        suggestion=comment_data["suggestion"]
                    )
                    comments.append(comment)
                except KeyError as e:
                    print(f"⚠️ コメントデータの解析中にエラー: {str(e)}")
                    continue
            
            return comments
            
        except Exception as e:
            print(f"❌ {role['role']}のレビュー中にエラー: {str(e)}")
            return []