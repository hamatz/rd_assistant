from typing import Dict, Optional, List, Any, Tuple
import asyncio
import traceback
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.status import Status
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.history import InMemoryHistory
from ..core.types import ProjectContext
from ..core.storage import SessionStorage  
from datetime import datetime 
from ..core.analyzer import RequirementAnalyzer
from ..core.organizer import RequirementsOrganizer
from ..core.visualizer import RequirementsVisualizer 
from ..core.memory import Requirement 
from ..core.editor import RequirementsEditor
from ..core.vision import VisionManager
from ..core.vision import FeaturePriority
from ..core.quality import RequirementQualityChecker

class InteractiveDialogue:
    def __init__(self, analyzer: RequirementAnalyzer, config: 'Config'):
        self.analyzer = analyzer
        self.config = config
        self.console = Console(force_terminal=True, color_system="auto")
        self.session = PromptSession(
            history=InMemoryHistory(),
            enable_history_search=True
        )
        self.storage = SessionStorage(config.get_session_config().get('save_dir', 'sessions'))
        self.is_running = True
        self.debug = config.get_debug_mode() 

    def _debug_log(self, message: str, data: Any = None):
        """デバッグログを出力"""
        if not self.debug:
            return

        styled_message = f"[steel_blue]DEBUG:[/steel_blue] {message}"

        if data is not None:
            if isinstance(data, str):
                styled_data = f"[green]'{data}'[/green]"
            elif isinstance(data, (list, dict)):
                styled_data = f"[green]{repr(data)}[/green]"
            else:
                styled_data = f"[green]{str(data)}[/green]"
            self.console.print(f"{styled_message} {styled_data}")
        else:
            self.console.print(styled_message)

    async def _process_single_interaction(self):
        """単一の対話処理"""
        try:
            user_input = await self.session.prompt_async("You: ")
            
            user_input = user_input.strip()
            if not user_input:
                return

            self._debug_log("受信したコマンド:", user_input)

            if await self._handle_command(user_input):
                return

            print("\n⚙️ 分析中...\n") 
            response = await self.analyzer.process_input(user_input)
            self._display_response(response)

        except Exception as e:
            self._handle_error(e)

    async def _handle_command(self, command: str) -> bool:
        """コマンドの処理を行う。コマンドとして処理された場合はTrueを返す"""
        command = command.lower().strip()
        self._debug_log("コマンドを処理中:", command)
        
        args = command.split()
        command_name = args[0]

        self._debug_log("コマンド名:", command_name)
        
        if command_name == "llm":
            return await self._handle_llm_command(args[1:])

        commands = {
            'exit': self._handle_exit,
            'quit': self._handle_exit,
            '終了': self._handle_exit,
            'status': self._show_status,
            '状態': self._show_status,
            'document': self._generate_document,
            'doc': self._generate_document,
            'ドキュメント': self._generate_document,
            'help': self._show_help,
            'ヘルプ': self._show_help,
            '?': self._show_help,
            'review': self._review_document,
            'レビュー': self._review_document,
            'save': self._save_session,
            '保存': self._save_session,
            'load': self._load_session,
            '読込': self._load_session,
            'list': self._list_sessions,
            '一覧': self._list_sessions,
            'edit': self._handle_edit_command,
            '編集': self._handle_edit_command,
            'vision': self._handle_vision_command,
            'ビジョン': self._handle_vision_command,
            'prioritize': self._handle_prioritize_command,
            '優先順位': self._handle_prioritize_command,
            'show-vision': self._show_vision,
            'ビジョン表示': self._show_vision,
            'quality': self._handle_quality_check_command,
            '品質': self._handle_quality_check_command,
            'organize': self._organize_requirements,
            '整理': self._organize_requirements
        }

        self._debug_log("利用可能なコマンド:", list(commands.keys()))
        
        handler = commands.get(command_name)
        if handler:
            self._debug_log(f"コマンドハンドラーが見つかりました: '{command_name}'")
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
                return True
            except Exception as e:
                self._handle_error(e)
                return True
        else:
            self._debug_log(f"コマンドハンドラーが見つかりません: '{command_name}'")
        
        return False

    async def start_dialogue(self):
        """対話セッションを開始"""
        try:
            self._show_welcome_message()
            await self._gather_project_info()
            
            with patch_stdout():
                while self.is_running:
                    try:
                        await self._process_single_interaction()
                    except asyncio.CancelledError:
                        self.console.print("[yellow]操作がキャンセルされました。[/yellow]")
                        continue
                    except KeyboardInterrupt:
                        if await self._confirm_exit():
                            break
                        continue
                    except EOFError:
                        break
                    except Exception as e:
                        self._handle_error(e)
                        if self.is_running:  # エラーで停止していない場合は続行
                            continue
                        else:
                            break
        
        finally:
            await self._cleanup()

    def _save_session(self):
        """現在のセッションを保存"""
        try:
            file_path = self.storage.save_session(self.analyzer.memory)
            print(f"\n✅ セッションを保存しました:")
            print(f"ファイル: {file_path}")
            print()
        except Exception as e:
            print(f"\n❌ セッションの保存に失敗しました: {str(e)}\n")

    async def _load_session(self):
        """保存されたセッションを読み込む"""
        sessions = self.storage.list_sessions()
        if not sessions:
            print("\n❌ 保存されたセッションが見つかりません。\n")
            return
        
        print("\n📁 保存されているセッション:")
        print("-" * 50)
        for i, session in enumerate(sessions):
            print(f"{i+1}. {session['project_name']}")
            print(f"   保存日時: {session['saved_at']}")
            print(f"   要件数: {session['requirements_count']}")
            print("-" * 30)
        
        try:
            selection = await self.session.prompt_async("読み込むセッション番号を入力してください（キャンセルはEnter）: ")
            if not selection.strip():
                return
            
            index = int(selection) - 1
            if 0 <= index < len(sessions):
                file_path = sessions[index]["file_path"]
                self.analyzer.memory = self.storage.load_session(file_path)
                print(f"\n✅ セッションを読み込みました: {self.analyzer.memory.project_name}\n")
            else:
                print("\n❌ 無効な番号です。\n")
        except ValueError:
            print("\n❌ 有効な数字を入力してください。\n")
        except Exception as e:
            print(f"\n❌ セッションの読み込みに失敗しました: {str(e)}\n")

    def _list_sessions(self):
            """保存されているセッションの一覧を表示"""
            sessions = self.storage.list_sessions()
            if not sessions:
                print("\n📁 保存されたセッションはありません。\n")
                return
            
            print("\n📁 保存されているセッション:")
            print("-" * 50)
            for session in sessions:
                print(f"プロジェクト: {session['project_name']}")
                print(f"保存日時: {session['saved_at']}")
                print(f"要件数: {session['requirements_count']}")
                print(f"制約数: {session['constraints_count']}")
                print(f"リスク数: {session['risks_count']}")
                print("-" * 30)
            print()

    async def _handle_exit(self):
        """終了処理"""
        if await self._confirm_exit():
            self.is_running = False

    async def _confirm_exit(self) -> bool:
        """終了確認"""
        try:
            response = await self.session.prompt_async("セッションを終了しますか？ (y/N): ")
            return response.lower().strip() in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            return True

    def _handle_error(self, error: Exception):
        """エラーハンドリング"""
        error_msg = str(error)
        error_type = type(error).__name__
        
        self.console.print(Panel(
            f"エラーが発生しました:\n"
            f"種類: {error_type}\n"
            f"詳細: {error_msg}",
            title="⚠️",
            style="red"
        ))

    async def _cleanup(self):
        """終了処理"""
        try:
            if self.analyzer.memory.requirements:  # 要件が存在する場合のみサマリーを表示
                await self._show_summary()
        except Exception as e:
            self.console.print(f"[red]終了処理中にエラーが発生しました: {str(e)}[/red]")

    async def _handle_edit_command(self):
        """要件の編集コマンドを処理"""
        if not self.analyzer.memory.requirements:
            print("\n⚠️ 編集可能な要件がありません。\n")
            return

        try:
            editor = RequirementsEditor(self.analyzer.llm_service)
            
            while True:
                print("\n📋 現在の要件一覧:")
                for i, req in enumerate(self.analyzer.memory.requirements):
                    print(editor.format_requirement_for_display(i, req))
                
                selection = await self.session.prompt_async("\n編集する要件の番号を入力してください（終了はEnter）: ")
                if not selection.strip():
                    break
                
                try:
                    index = int(selection) - 1
                    if 0 <= index < len(self.analyzer.memory.requirements):
                        requirement = self.analyzer.memory.requirements[index]

                        print("\n編集する項目を選択してください：")
                        print("1. 内容")
                        print("2. 種類")
                        print("3. 理由")
                        
                        edit_type = await self.session.prompt_async("項目の番号を入力してください: ")
                        if edit_type not in ['1', '2', '3']:
                            print("❌ 無効な選択です。")
                            continue

                        edit_types = {
                            '1': 'content',
                            '2': 'type',
                            '3': 'rationale'
                        }

                        if edit_type == '2':
                            print("\n要件の種類を選択してください：")
                            print("1. functional（機能要件）")
                            print("2. non_functional（非機能要件）")
                            print("3. technical（技術要件）")
                            print("4. business（ビジネス要件）")
                            type_selection = await self.session.prompt_async("番号を入力してください: ")
                            type_mapping = {
                                '1': 'functional',
                                '2': 'non_functional',
                                '3': 'technical',
                                '4': 'business'
                            }
                            if type_selection not in type_mapping:
                                print("❌ 無効な選択です。")
                                continue
                            new_value = type_mapping[type_selection]
                        else:
                            new_value = await self.session.prompt_async("新しい値を入力してください: ")
                        
                        if not new_value.strip():
                            print("❌ 値が入力されていません。")
                            continue

                        edited_requirement = await editor.edit_requirement(
                            requirement,
                            edit_types[edit_type],
                            new_value
                        )
                        
                        if edited_requirement:
                            print("\n📝 変更後の要件:")
                            print(editor.format_requirement_for_display(index, edited_requirement))
                            
                            confirm = await self.session.prompt_async("この変更を適用しますか？ (Y/n): ")
                            if confirm.lower().strip() not in ['n', 'no']:
                                self.analyzer.memory.update_requirement(
                                    self.analyzer.memory.requirements[index],
                                    {
                                        "content": edited_requirement.content,
                                        "type": edited_requirement.type,
                                        "rationale": edited_requirement.rationale,
                                        "metadata": edited_requirement.metadata
                                    }
                                )
                                print("✅ 要件を更新しました。")
                                
                                save_confirm = await self.session.prompt_async("変更を保存しますか？ (Y/n): ")
                                if save_confirm.lower().strip() not in ['n', 'no']:
                                    self._save_session()
                        
                    else:
                        print("❌ 無効な番号です。")
                
                except ValueError:
                    print("❌ 有効な数字を入力してください。")
                except Exception as e:
                    print(f"❌ エラーが発生しました: {str(e)}")
                
                continue_edit = await self.session.prompt_async("\n他の要件も編集しますか？ (y/N): ")
                if continue_edit.lower().strip() not in ['y', 'yes']:
                    break
        
        except Exception as e:
            print(f"❌ 編集処理中にエラーが発生しました: {str(e)}")

    async def _organize_requirements(self):
            """要件の再整理を行う"""
            if not self.analyzer.memory.requirements:
                print("\n⚠️ 要件がまだ登録されていません。\n")
                return

            print("\n🔄 要件の再整理を開始します...")
            
            try:
                organizer = RequirementsOrganizer(self.analyzer.llm_service)
                result = await organizer.organize_requirements(self.analyzer.memory)
                
                print("\n📋 再整理の結果:")
                print("-" * 50)

                print("変更点:")
                for change in result.changes_made:
                    print(f"- {change['type']}: {change['description']}")
                print()

                print("再整理された要件:")
                for i, req in enumerate(result.organized_requirements, 1):
                    print(f"\n{i}. {req.content}")
                    print(f"   種類: {req.type}")
                    print(f"   理由: {req.rationale}")
                print()

                if result.suggestions:
                    print("提案事項:")
                    for suggestion in result.suggestions:
                        print(f"- {suggestion}")
                    print()

                if await self._confirm_changes():
                    self._save_session()
                    self.analyzer.memory.record_organization(result.changes_made)
                    self.analyzer.memory.requirements = result.organized_requirements
                    print("\n✅ 要件を更新しました。\n")
                else:
                    print("\n⚠️ 変更を取り消しました。\n")
                    
            except Exception as e:
                print(f"\n❌ 再整理中にエラーが発生しました: {str(e)}\n")

    async def _confirm_changes(self) -> bool:
        """変更の適用を確認"""
        try:
            response = await self.session.prompt_async("これらの変更を適用しますか？ (y/N): ")
            return response.lower().strip() in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            return False

    async def _review_document(self):
        """要件定義書のレビューを実行"""
        try:
            if not self.analyzer.memory.requirements:
                print("\n⚠️ 要件がまだ登録されていません。\n")
                return

            print("\n🔍 要件定義書のレビューを開始します...")
            
            try:
                print("\n📄 要件定義書を生成中...")
                from ..core.document import DocumentGenerator
                generator = DocumentGenerator(self.analyzer.memory)
                document = generator.generate_markdown()
                print("✅ 要件定義書の生成が完了しました")
                
                print("\n🔍 レビューを実行中...")
                from ..core.reviewer import RequirementsReviewer
                reviewer = RequirementsReviewer(self.analyzer.llm_service)

                print("\n📊 レビュー処理の詳細:")
                print("- 要件数:", len(self.analyzer.memory.requirements))
                print("- 制約数:", len(self.analyzer.memory.constraints))
                print("- リスク数:", len(self.analyzer.memory.risks))
                
                result = await reviewer.review_requirements(self.analyzer.memory, document)
                print("✅ レビューが完了しました")
                
                self._display_review_results(result)
                
                if result.improvement_suggestions and await self._confirm_review_changes(result):
                    await self._apply_review_suggestions(result)
                    print("\n✅ 要件を更新しました。\n")
                else:
                    print("\n⚠️ 変更を適用せずに終了します。\n")
                    
            except asyncio.TimeoutError:
                print("\n⚠️ レビュー処理がタイムアウトしました。再試行してください。\n")
            except Exception as e:
                print(f"\n❌ レビュー中にエラーが発生しました: {str(e)}\n")
                print("エラーの詳細:")
                import traceback
                print(traceback.format_exc())
                
        except Exception as e:
            self.console.print(f"[red]レビュー処理中にエラーが発生しました: {str(e)}[/red]")
            import traceback
            self.console.print(f"[dim]エラーの詳細:\n{traceback.format_exc()}[/dim]")

    def _display_review_results(self, result):
        """レビュー結果の表示"""
        print("\n📋 レビュー結果:")
        print("=" * 50)

        visualizer = RequirementsVisualizer()

        print("\n🗺️ 要件の全体像:")
        tree_view = visualizer.generate_text_tree(self.analyzer.memory)
        print(tree_view)
        print()

        print("\n🔄 要件の関係性:")
        flow_view = visualizer.generate_text_flow(self.analyzer.memory)
        print(flow_view)
        print()
        
        print("\n📊 総合評価:")
        print("-" * 30)
        print(result.overall_evaluation)

        if result.comments:
            print("\n💬 専門家からのフィードバック:")
            print("-" * 30)
            
            importance_order = {"high": 0, "medium": 1, "low": 2}
            sorted_comments = sorted(
                result.comments,
                key=lambda x: importance_order[x.importance]
            )
            
            for comment in sorted_comments:
                if comment.importance == "high":
                    print(f"\n🔴 {comment.role}:")
                elif comment.importance == "medium":
                    print(f"\n🟡 {comment.role}:")
                else:
                    print(f"\n⚪ {comment.role}:")
                print(f"分類: {comment.category}")
                print(f"コメント: {comment.content}")
                print(f"提案: {comment.suggestion}")
        
        if result.improvement_suggestions:
            print("\n✨ 改善提案:")
            print("-" * 30)
            for i, suggestion in enumerate(result.improvement_suggestions, 1):
                print(f"\n提案 {i}:")
                print(f"優先度: {suggestion.get('priority', 'N/A')}")
                print(f"領域: {suggestion.get('area', 'N/A')}")
                print(f"内容: {suggestion.get('suggestion', 'N/A')}")
                print(f"理由: {suggestion.get('rationale', 'N/A')}")
        
        print("=" * 50 + "\n")

    def _display_mermaid_diagram(self, title: str, content: str):
        """Mermaidダイアグラムを表示"""
        from rich.panel import Panel
        
        diagram = f"```mermaid\n{content}\n```"
        
        self.console.print(Panel(
            diagram,
            title=f"📊 {title}",
            border_style="blue"
        ))

    async def _confirm_review_changes(self, result) -> bool:
        """レビューに基づく変更の確認"""
        print("\n変更を適用する前に、以下の点について確認してください：")
        print("1. 提案された改善点は妥当ですか？")
        print("2. 技術的な実現可能性は検討されていますか？")
        print("3. ビジネス目標との整合性は取れていますか？")
        
        try:
            response = await self.session.prompt_async("\nこれらの改善提案を適用しますか？ (y/N): ")
            return response.lower().strip() in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            return False

    async def _apply_review_suggestions(self, result):
        """レビューの提案を対話的に適用"""
        applied_suggestions = set()
        
        while True:
            remaining_suggestions = [
                (i, suggestion) 
                for i, suggestion in enumerate(result.improvement_suggestions) 
                if i not in applied_suggestions
            ]
            
            if not remaining_suggestions:
                print("\n✨ すべての提案が適用されました。")
                break
            
            print("\n📋 未適用の改善提案:")
            print("-" * 50)
            for i, suggestion in remaining_suggestions:
                print(f"[{i+1}] {suggestion['area']}: {suggestion['suggestion']}")
                print(f"    理由: {suggestion['rationale']}")
                print(f"    優先度: {suggestion['priority']}")
                print()
            
            print("\n適用する提案の番号を入力してください（複数の場合はカンマ区切り）")
            print("スキップする場合は N を入力してください")
            
            try:
                response = await self.session.prompt_async("選択 (例: 1,3,5 または N): ")
                if response.lower().strip() == 'n':
                    if remaining_suggestions:
                        confirm = await self.session.prompt_async(
                            "未適用の提案が残っていますが、本当に終了しますか？ (y/N): "
                        )
                        if confirm.lower().strip() not in ['y', 'yes']:
                            continue
                    break

                try:
                    selected_indices = [int(idx.strip()) - 1 for idx in response.split(',')]

                    valid_indices = [i for i, _ in remaining_suggestions]
                    if not all(idx in valid_indices for idx in selected_indices):
                        print("❌ 無効な番号が含まれています。")
                        continue
                    
                    selected_suggestions = [
                        result.improvement_suggestions[idx] 
                        for idx in selected_indices
                    ]
                except (ValueError, IndexError):
                    print("❌ 無効な入力です。正しい番号を入力してください。")
                    continue

                for idx, suggestion in zip(selected_indices, selected_suggestions):
                    if await self._generate_and_append_requirement(suggestion):
                        applied_suggestions.add(idx)

                if remaining_suggestions:
                    continue_response = await self.session.prompt_async(
                        "\n他の提案も適用しますか？ (Y/n): "
                    )
                    if continue_response.lower().strip() in ['n', 'no']:
                        break
                else:
                    print("\n✨ すべての提案が適用されました。")
                    break

            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                print(f"❌ エラーが発生しました: {str(e)}")
                continue

    async def _generate_and_append_requirement(self, suggestion) -> bool:
        """提案に基づいて新しい要件を生成し追加。成功した場合はTrueを返す"""
        prompt = f"""
    以下の改善提案に基づいて、具体的な要件定義の文章を生成してください：

    改善領域: {suggestion['area']}
    提案内容: {suggestion['suggestion']}
    提案理由: {suggestion['rationale']}

    現在のプロジェクト概要:
    {self.analyzer.memory.project_description}

    以下の形式でJSONとして回答してください：
    {{
        "requirement": {{
            "type": "functional|non_functional|technical|business",
            "content": "要件の内容",
            "rationale": "この要件が必要な理由や背景",
            "confidence": 0.0-1.0,
            "implicit": false
        }}
    }}
    """
        try:
            response = await self.analyzer.llm_service.generate_response(prompt)
            
            if 'requirement' in response:
                req_data = response['requirement']
                new_requirement = Requirement(
                    content=req_data['content'],
                    type=req_data['type'],
                    confidence=req_data['confidence'],
                    rationale=req_data['rationale'],
                    implicit=req_data['implicit'],
                    created_at=datetime.now() 
                )
                
                print("\n📝 生成された要件:")
                print("-" * 30)
                print(f"種類: {new_requirement.type}")
                print(f"内容: {new_requirement.content}")
                print(f"理由: {new_requirement.rationale}")
                print("-" * 30)
                
                confirm = await self.session.prompt_async("この要件を追加しますか？ (Y/n): ")
                if confirm.lower().strip() not in ['n', 'no']:
                    self.analyzer.memory.requirements.append(new_requirement)
                    print("✅ 要件を追加しました。")
                    return True
                else:
                    print("⚠️ 要件の追加をスキップしました。")
                    return False
            
            return False
                
        except Exception as e:
            print(f"❌ 要件の生成中にエラーが発生しました: {str(e)}")
            return False

    async def _handle_llm_command(self, args: list) -> bool:
            """LLM関連コマンドの処理"""
            if not args:
                self._show_llm_config()
                return True

            if args[0] == "config":
                self._show_llm_config()
                return True

            if args[0] == "set" and len(args) >= 3:
                setting = args[1]
                value = args[2]
                
                try:
                    if setting == "provider":
                        self.config.update_llm_config({"provider": value})
                        print(f"✅ LLMプロバイダーを {value} に設定しました")
                    elif setting == "model":
                        self.config.update_llm_config({"model": value})
                        print(f"✅ モデルを {value} に設定しました")
                    elif setting == "key":
                        self.config.update_llm_config({"api_key": value})
                        print("✅ APIキーを更新しました")
                    else:
                        print(f"❌ 未知の設定: {setting}")
                        return True

                    self.analyzer.llm_service = LLMServiceFactory.create(self.config.get_llm_config())
                    
                except Exception as e:
                    print(f"❌ 設定の更新に失敗しました: {str(e)}")
                
                return True

            return False

    def _show_llm_config(self):
        """現在のLLM設定を表示"""
        config = self.config.get_llm_config()
        print("\n🔧 現在のLLM設定:")
        print("-" * 50)
        print(f"プロバイダー: {config.provider}")
        print(f"モデル: {config.model}")
        print(f"APIキー: {'設定済み' if config.api_key else '未設定'}")
        if config.api_base:
            print(f"APIベースURL: {config.api_base}")
        if config.deployment_name:
            print(f"デプロイメント名: {config.deployment_name}")
        print(f"Temperature: {config.temperature}")
        print(f"最大トークン数: {config.max_tokens}")
        print("-" * 50)
        print()

    def _show_help(self):
            """ヘルプメッセージの表示"""
            print("\n💡 ヘルプ")
            print("=" * 50)
            print("使用可能なコマンド:")
            print("- status/状態: 現在の分析状況を表示")
            print("- document/doc/ドキュメント: 現時点の要件定義書を生成")
            print("- llm config: 現在のLLM設定を表示")
            print("- llm set provider <provider>: LLMプロバイダーを設定 (azure/openai/anthropic)")
            print("- llm set model <model>: モデルを設定")
            print("- llm set key <api_key>: APIキーを設定")
            print("- review/レビュー： LLMによる要件定義書のレビューを実行")
            print("- vison/ビジョン： プロジェクトのビジョンをクリアにする")
            print("- show-vision/ビジョン表示： プロジェクトのビジョンを表示する")
            print("- quality/品質： 要件の品質チェックを実行")
            print("- organize/整理: 要件の再整理を実行")
            print("- prioritize/優先順位: 要件の優先順位付けを実行") 
            print("- save/保存: 現在のセッションを保存")
            print("- load/読込: 保存されたセッションを読み込む")
            print("- edit/編集：登録済みの要件を編集する")
            print("- list/一覧: 保存されているセッションを表示")
            print("- help/ヘルプ/?: このヘルプメッセージを表示")
            print("- exit/quit/終了: セッションを終了")
            print("\nその他の操作:")
            print("- Ctrl+C: 現在の操作をキャンセル")
            print("- Ctrl+D: セッションを終了")
            print("- ↑↓: 入力履歴の表示")
            print("=" * 50)
            print()

    def _show_welcome_message(self):
        print("\n💡 要件定義支援システム")
        print("=" * 50)
        print("こんにちは！プロジェクトの要件定義のお手伝いをさせていただきます。")
        print("プロジェクトについて、どんなことでも構いませんのでお聞かせください。")
        print("\n使用可能なコマンド:")
        print("- load/読込: 保存されたセッションを読み込む")
        print("- save/保存: 現在のセッションを保存する")
        print("- list/一覧: 保存されているセッションを表示する")
        print("- help/ヘルプ/?: コマンド一覧を表示")
        print("=" * 50)
        print()

    async def _gather_project_info(self):
        """プロジェクト情報の収集"""
        print("\n📋 プロジェクト概要を教えてください")
        print("-" * 50)
        
        name = await self.session.prompt_async("プロジェクト名: ")
        description = await self.session.prompt_async("概要: ")
        
        self.analyzer.set_project_info(name, description)
        
        print("\n✅ プロジェクト情報を保存しました。\n")
        print("それでは、プロジェクトの要件について教えてください。")
        print("自然な会話の中から要件を抽出していきます。\n")
        print("最初に vision コマンドを実行し、プロジェクトのビジョンを登録しておくのがオススメです。\n")

    def _display_response(self, response: Dict):
        """応答の表示"""
        if 'response' in response:
            print("\n🤖 システム:")
            print("-" * 50)
            print(response['response']['message'])
            print("-" * 50)

            if 'analysis' in response and 'extracted_requirements' in response['analysis']:
                requirements = [
                    req for req in response['analysis']['extracted_requirements']
                    if req['confidence'] > 0.8
                ]
                if requirements:
                    self._show_extracted_requirements(requirements)

            if 'analysis' in response and 'potential_risks' in response['analysis']:
                risks = response['analysis']['potential_risks']
                if risks:
                    self._show_risks(risks)

    def _show_extracted_requirements(self, requirements: list):
        """抽出された要件の表示"""
        print("\n📋 抽出された要件:")
        print("-" * 50)
        for req in requirements:
            confidence = f"{req['confidence']*100:.1f}%"
            print(f"種類: {req['type']}")
            print(f"内容: {req['content']}")
            print(f"確信度: {confidence}")
            print("-" * 30)
        print()

    def _show_risks(self, risks: list):
        """リスクの表示"""
        print("\n⚠️ 検出されたリスク:")
        print("-" * 50)
        for risk in risks:
            print(f"深刻度: {risk['severity']}")
            print(f"内容: {risk['description']}")
            print(f"対策案: {risk['mitigation']}")
            print("-" * 30)
        print()

    def _show_status(self):
        """現在の分析状況を表示"""
        status = self.analyzer.get_current_status()
        summary = self.analyzer.get_requirements_summary()
        
        print("\n📊 現在の分析状況:")
        print("-" * 50)
        print(f"機能要件: {summary['functional']['count']}")
        print(f"非機能要件: {summary['non_functional']['count']}")
        print(f"技術要件: {summary['technical']['count']}")
        print(f"ビジネス要件: {summary['business']['count']}")
        print(f"制約条件: {status['constraints_count']}")
        print(f"検出リスク: {status['risks_count']}")
        print("-" * 50)
        print()

    async def _show_summary(self):
        """セッションの要約を表示してドキュメントを生成"""
        self.console.print(Panel(
            "セッションを終了します。要約を生成中...",
            style="blue"
        ))
        
        self._show_status()
 
        await self._generate_document()

    async def _generate_document(self):
        """現時点での要件定義書を生成"""
        from ..core.document import DocumentGenerator
        generator = DocumentGenerator(self.analyzer.memory)
        
        try:
            file_path = generator.save_document()
            self.console.print(Panel(
                f"要件定義書を生成しました:\n{file_path}",
                title="📄 ドキュメント生成完了",
                style="green"
            ))
        except Exception as e:
            self.console.print(Panel(
                f"ドキュメントの生成中にエラーが発生しました: {str(e)}",
                title="❌ エラー",
                style="red"
            ))

    async def _handle_vision_command(self):
        """ビジョン関連のコマンドを処理"""
        vision_manager = VisionManager(self.analyzer.llm_service)
        
        try:
            if self.analyzer.memory.project_vision:
                print("\n現在のプロジェクトビジョン:")
                print("=" * 50)
                print(vision_manager.format_vision_summary(self.analyzer.memory.project_vision))
                print("=" * 50)

                print("\n実行したいアクションを選択してください：")
                print("1. ビジョンを更新する")
                print("2. 優先順位を更新する")
                print("3. 現在のビジョンを維持する")
                
                action = await self.session.prompt_async("\n選択 (1-3): ")
                
                if action == "1":
                    await self._update_vision(vision_manager)
                elif action == "2":
                    await self._update_priorities(vision_manager)
                else:
                    print("\n✓ 現在のビジョンを維持します。")
                    return
            else:
                await self._create_new_vision(vision_manager)
            
            save_confirm = await self.session.prompt_async("\n変更を保存しますか？ (Y/n): ")
            if save_confirm.lower().strip() not in ['n', 'no']:
                self._save_session()
        
        except Exception as e:
            print(f"❌ ビジョン管理中にエラーが発生しました: {str(e)}")

    async def _create_new_vision(self, vision_manager: 'VisionManager'):
        """新規ビジョンの作成"""
        print("\n🎯 プロジェクトビジョンを整理します。")
        print("以下の質問に答えてください：")
        
        responses = []
        questions = [
        "このプロジェクトの主な目的は何ですか？できるだけ具体的に教えてください。",
        "想定しているユーザーはどのような人たちですか？具体的な属性や特徴を教えてください。",
        "プロジェクトが成功したと判断する基準は何ですか？できれば数値目標なども含めて教えてください。",
        "現時点で認識している制約や課題はありますか？技術面、コスト面、時間面など。",
        "このプロジェクトで特に重視したい要素は何ですか？（例：使いやすさ、セキュリティ、パフォーマンスなど）理由も含めて教えてください。"
        ]
        
        for question in questions:
            response = await self.session.prompt_async(f"\n{question}\n回答: ")
            responses.append(f"Q: {question}\nA: {response}")
        
        vision = await vision_manager.extract_vision_from_conversation("\n\n".join(responses))
        await self._confirm_and_save_vision(vision_manager, vision)

    async def _update_vision(self, vision_manager: 'VisionManager'):
        """既存ビジョンの更新"""
        print("\n🔄 ビジョンの更新を行います。")
        print("現在の内容を確認しながら、必要に応じて更新してください。")
        
        current_vision = self.analyzer.memory.project_vision
        responses = []

        sections = [
            ("目標", current_vision.goals, "プロジェクトの目標を更新しますか？"),
            ("対象ユーザー", current_vision.target_users, "対象ユーザーの定義を更新しますか？"),
            ("成功基準", current_vision.success_criteria, "成功基準を更新しますか？"),
            ("制約事項", current_vision.constraints, "制約事項を更新しますか？")
        ]
        
        for section_name, current_items, question in sections:
            print(f"\n現在の{section_name}:")
            for item in current_items:
                print(f"  ・{item}")
            
            update = await self.session.prompt_async(f"\n{question} (y/N): ")
            if update.lower().strip() in ['y', 'yes']:
                new_response = await self.session.prompt_async(f"\n新しい{section_name}を入力してください: ")
                responses.append(f"Q: {section_name}について更新してください\nA: {new_response}")
        
        if responses:
            context = "\n\n".join([
                "現在のビジョン:",
                vision_manager.format_vision_summary(current_vision),
                "\n更新内容:",
                "\n\n".join(responses)
            ])
            
            updated_vision = await vision_manager.extract_vision_from_conversation(context)
            await self._confirm_and_save_vision(vision_manager, updated_vision)
        else:
            print("\n✓ 更新はありませんでした。")

    async def _update_priorities(self, vision_manager: 'VisionManager'):
        """優先順位の更新"""
        if not self.analyzer.memory.requirements:
            print("\n⚠️ 優先順位付けを行う要件がありません。")
            return
        
        print("\n📊 要件の優先順位付けを行います。")
        features = [req.content for req in self.analyzer.memory.requirements]
        priorities = await vision_manager.prioritize_features(
            features,
            self.analyzer.memory.project_vision
        )
        
        print("\n優先順位の分析結果:")
        print(vision_manager.format_priority_summary(priorities))
        
        confirm = await self.session.prompt_async("\nこの優先順位付けで良いですか？ (Y/n): ")
        if confirm.lower().strip() not in ['n', 'no']:
            self.analyzer.memory.update_priorities(priorities)
            print("✅ 優先順位を更新しました。")

    async def _prioritize_requirements(self, vision_manager: 'VisionManager'):
        """要件の優先順位付けを対話的に実行"""
        if not self.analyzer.memory.requirements:
            print("\n⚠️ 優先順位付けを行う要件がありません。")
            return

        print("\n📊 要件の優先順位付けを行います。")
        print("各要件について、プロジェクトの目標達成における重要度を確認していきます。")
        
        priorities: List[FeaturePriority] = []
        priority_descriptions = {
            "must_have": "🔴 Must Have - プロジェクトの成功に不可欠",
            "should_have": "🟡 Should Have - 重要だが必須ではない",
            "could_have": "🟢 Could Have - あると良いが後回し可能",
            "won't_have": "⚪ Won't Have - 現時点では対象外"
        }

        for req in self.analyzer.memory.requirements:
            print(f"\n📝 要件の分析中: {req.content}")

            analysis = await vision_manager.get_feature_priority(req.content, self.analyzer.memory.project_vision)
            
            if not analysis:
                print("⚠️ この要件の分析をスキップします。")
                continue

            print("\n分析結果:")
            print(f"重要度: {analysis.get('necessity_level', 'N/A')}")
            print(f"影響: {analysis.get('impact', 'N/A')}")
            print(f"遅延リスク: {analysis.get('delay_risk', 'N/A')}")
            
            suggested_priority = analysis.get('suggested_priority', 'could_have')
            print(f"\n推奨優先度: {priority_descriptions.get(suggested_priority, 'N/A')}")
            print(f"理由: {analysis.get('rationale', 'N/A')}")

            print("\n優先度の選択:")
            for key, desc in priority_descriptions.items():
                print(f"{desc}")
            
            while True:
                print("\n優先度を選択してください：")
                print("1. Must Have")
                print("2. Should Have")
                print("3. Could Have")
                print("4. Won't Have")
                print("5. この要件の優先度付けをスキップ")
                
                choice = await self.session.prompt_async("選択 (1-5): ")
                
                priority_map = {
                    "1": "must_have",
                    "2": "should_have",
                    "3": "could_have",
                    "4": "won't_have"
                }
                
                if choice == "5":
                    print("⚠️ この要件をスキップします。")
                    break
                elif choice in priority_map:
                    selected_priority = priority_map[choice]

                    dependencies = []
                    if selected_priority == "must_have":
                        print("\nこの要件が依存する他の要件はありますか？")
                        print("（複数ある場合はカンマ区切りで入力してください）")
                        deps = await self.session.prompt_async("依存要件の番号（なければEnter）: ")
                        if deps.strip():
                            dep_indices = [int(i.strip()) - 1 for i in deps.split(",")]
                            dependencies = [self.analyzer.memory.requirements[i].content 
                                        for i in dep_indices 
                                        if 0 <= i < len(self.analyzer.memory.requirements)]
                    
                    priorities.append(FeaturePriority(
                        feature=req.content,
                        priority=selected_priority,
                        rationale=analysis.get('rationale', ''),
                        dependencies=dependencies
                    ))
                    break
                else:
                    print("❌ 無効な選択です。")
        
        if priorities:
            print("\n📋 設定された優先順位:")
            for priority_type in ["must_have", "should_have", "could_have", "won't_have"]:
                features = [p for p in priorities if p.priority == priority_type]
                if features:
                    print(f"\n{priority_descriptions[priority_type]}:")
                    for feature in features:
                        print(f"  ・{feature.feature}")
                        if feature.dependencies:
                            print(f"    依存: {', '.join(feature.dependencies)}")
            
            confirm = await self.session.prompt_async("\nこの優先順位付けで確定しますか？ (Y/n): ")
            if confirm.lower().strip() not in ['n', 'no']:
                self.analyzer.memory.update_priorities(priorities)
                print("✅ 優先順位を更新しました。")
                
                save_confirm = await self.session.prompt_async("変更を保存しますか？ (Y/n): ")
                if save_confirm.lower().strip() not in ['n', 'no']:
                    self._save_session()
        else:
            print("\n⚠️ 優先順位が設定されませんでした。")

    async def _handle_prioritize_command(self):
        """優先順位付けコマンドのハンドラ"""
        try:
            if not self.analyzer.memory.project_vision:
                print("\n⚠️ まずプロジェクトビジョンを設定してください。")
                print("'vision' コマンドを使用してビジョンを設定できます。")
                return

            vision_manager = VisionManager(self.analyzer.llm_service)
            await self._prioritize_requirements(vision_manager)
        except Exception as e:
            print(f"❌ 優先順位付けでエラーが発生しました: {str(e)}")

    async def _confirm_and_save_vision(self, vision_manager: 'VisionManager', vision: 'ProjectVision'):
        """ビジョンの確認と保存"""
        print("\n📋 更新後のプロジェクトビジョン:")
        print(vision_manager.format_vision_summary(vision))
        
        confirm = await self.session.prompt_async("\nこのビジョンで良いですか？ (Y/n): ")
        if confirm.lower().strip() not in ['n', 'no']:
            self.analyzer.memory.update_vision(vision)
            print("✅ プロジェクトビジョンを更新しました。")

    def _show_vision(self):
        """現在のプロジェクトビジョンを表示"""
        if not self.analyzer.memory.project_vision:
            print("\n⚠️ プロジェクトビジョンはまだ定義されていません。")
            print("'vision' コマンドを使用してビジョンを設定できます。")
            return
        
        vision_manager = VisionManager(self.analyzer.llm_service)
        
        print("\n📋 プロジェクトビジョン")
        print("=" * 50)
        print(vision_manager.format_vision_summary(self.analyzer.memory.project_vision))
        
        if self.analyzer.memory.feature_priorities:
            print("\n📊 機能の優先順位")
            print("=" * 50)
            print(vision_manager.format_priority_summary(self.analyzer.memory.feature_priorities))
        
        print("=" * 50)

    async def _handle_quality_check_command(self):
        """要件の品質チェックを実行"""
        if not self.analyzer.memory.requirements:
            print("\n⚠️ チェックする要件がありません。")
            return

        from ..core.quality import RequirementQualityChecker
        checker = RequirementQualityChecker()
        
        print("\n📊 要件の品質チェックを実行します...")

        total_reqs = len(self.analyzer.memory.requirements)
        quality_scores = []
        
        for i, req in enumerate(self.analyzer.memory.requirements, 1):
            print(f"\n[{i}/{total_reqs}] 要件を分析中: {req.content[:50]}...")
            score = await checker.analyze_requirement(req, self.analyzer.memory, self.analyzer.llm_service)
            quality_scores.append((req, score))
            self.analyzer.memory.record_review(
                req=req,
                quality_score=score.total,
                suggestions=score.suggestions
            )

        self._display_quality_summary(quality_scores)
        
        sorted_scores = sorted(quality_scores, key=lambda x: x[1].total, reverse=True)
        
        print("\n📋 各要件の詳細分析:")
        print("=" * 50)

        critical_issues = []
        for req, score in sorted(quality_scores, key=lambda x: x[1].total):
            if score.total < 0.6:
                critical_issues.append((req, score))
        
        if critical_issues:
            print("\n⚠️ 優先的に改善が必要な要件:")
            print("-" * 50)
            for req, score in critical_issues:
                self._display_quality_result(req, score)
            print("\n" + "=" * 50)
        
        for req, score in sorted_scores:
            if score.total >= 0.6:
                self._display_quality_result(req, score)

        self._display_overall_suggestions(quality_scores)

    def _display_quality_summary(self, quality_scores: List[Tuple[Requirement, 'DetailedQualityScore']]):
        """品質チェックの全体サマリーを表示"""
        print("\n📈 品質チェック サマリー")
        print("=" * 50)

        total_reqs = len(quality_scores)
        average_score = sum(score.total for _, score in quality_scores) / total_reqs
        min_score = min(score.total for _, score in quality_scores)
        max_score = max(score.total for _, score in quality_scores)
        
        print(f"\n総要件数: {total_reqs}")
        print(f"平均品質スコア: {average_score:.2f}")
        print(f"最高スコア: {max_score:.2f}")
        print(f"最低スコア: {min_score:.2f}")
        
        score_ranges = {
            "優れている (0.8-1.0)": len([s for _, s in quality_scores if s.total >= 0.8]),
            "良好 (0.6-0.8)": len([s for _, s in quality_scores if 0.6 <= s.total < 0.8]),
            "改善の余地あり (0.4-0.6)": len([s for _, s in quality_scores if 0.4 <= s.total < 0.6]),
            "要改善 (0.0-0.4)": len([s for _, s in quality_scores if s.total < 0.4])
        }
        
        print("\n品質スコア分布:")
        for range_name, count in score_ranges.items():
            percentage = (count / total_reqs) * 100
            bar = "▓" * int(percentage / 5)  # 5%ごとに1文字
            print(f"{range_name}: {count}件 ({percentage:.1f}%) {bar}")

    def _display_quality_result(self, req: Requirement, score: 'DetailedQualityScore'):
        """個別要件の品質チェック結果を表示"""
        def get_score_emoji(value: float) -> str:
            if value >= 0.8: return "🟢"
            if value >= 0.6: return "🟡"
            return "🔴"
        
        print(f"\n要件: {req.content}")
        print(f"種類: {req.type}")

        score_groups = {
            "基本要素": {
                "具体性": score.specificity,
                "測定可能性": score.measurability,
                "明確さ": score.clarity
            },
            "実現性": {
                "実現可能性": score.achievability,
                "完全性": score.completeness
            },
            "プロジェクト適合性": {
                "関連性": score.relevance,
                "ビジョン整合性": score.vision_alignment,
                "用語一貫性": score.consistency
            }
        }

        print(f"\n総合スコア: {get_score_emoji(score.total)} {score.total:.2f}")

        for group_name, metrics in score_groups.items():
            print(f"\n{group_name}:")
            for metric_name, value in metrics.items():
                emoji = get_score_emoji(value)
                print(f"{emoji} {metric_name}: {value:.2f}")

        if score.details:
            print("\n🔍 検出された問題:")
            for category, detail in score.details.items():
                print(f"- {detail}")

        if score.suggestions:
            print("\n💡 改善提案:")
            for suggestion in score.suggestions:
                if isinstance(suggestion, str):
                    print(f"- {suggestion}")
                else:
                    print(f"- {suggestion['point']}")
                    if 'reason' in suggestion:
                        print(f"  理由: {suggestion['reason']}")
                    if 'expected_impact' in suggestion:
                        print(f"  期待される効果: {suggestion['expected_impact']}")
        
        print("-" * 50)

    def _display_overall_suggestions(self, quality_scores: List[Tuple[Requirement, 'DetailedQualityScore']]):
        """全体的な改善提案を表示"""
        print("\n📝 全体的な改善提案")
        print("=" * 50)

        metrics = {
            "specificity": ("具体性", []),
            "measurability": ("測定可能性", []),
            "clarity": ("明確さ", []),
            "consistency": ("一貫性", []),
            "completeness": ("完全性", []),
            "vision_alignment": ("ビジョン整合性", [])
        }
        
        for req, score in quality_scores:
            for metric, (label, issues) in metrics.items():
                value = getattr(score, metric)
                if value < 0.6:
                    issues.append(req.content)

        for metric, (label, issues) in metrics.items():
            if issues:
                print(f"\n{label}に関する改善が必要な要件: {len(issues)}件")
                for issue in issues[:3]:  # 最大3件まで表示
                    print(f"- {issue}")
                if len(issues) > 3:
                    print(f"- その他 {len(issues) - 3}件...")
        
        print("\n" + "=" * 50)