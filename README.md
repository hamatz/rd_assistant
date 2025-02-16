# 要件定義が楽しくなる！ AIと一緒に育てる要件定義「RD-Assistant」

## AIと一緒に要件を育てる

「要件定義」という言葉を聞いて、どんなイメージを持ちますか？

- 堅苦しい文書作成作業？
- チェックリストと格闘する時間？
- 完璧を目指して疲弊する日々？

RD-Assistant は、そんなイメージを一新します。まるで経験豊富なアナリストとおしゃべりするように、要件を育てていけるツールです。

## 対話から始まる要件定義

最初は、プロジェクトのビジョンを共有するところから始まります：

```bash
You: vision

🎯 プロジェクトビジョンを整理します。
以下の質問に答えてください：

このプロジェクトの主な目的は何ですか？
回答: 友達の情報を記憶補助的に管理して、コミュニケーションを円滑にしたい

想定しているユーザーはどのような人たちですか？
回答: 大学生から30代くらいまでの社会人

プロジェクトが成功したと判断する基準は何ですか？
回答: ユーザーの8割以上が継続的に利用してくれること
```

ビジョンを共有した後は、思いついた要件を自由に話しかけます：

```bash
You: プロフィール情報として、アバター画像、名前、趣味、メモなどを登録できると良いです

🤖 システム:
なるほど、ユーザープロフィール機能について具体的な要件が出てきましたね。
これらの情報は個人のプライバシーに関わるデータですので、
セキュリティ面でも考慮が必要そうです。

以下の要件を追加しました：
- プロフィール情報（アバター画像、名前、趣味、メモ）の登録機能
- ユーザーデータのセキュアな管理機能

他に考慮すべき点として：
1. プロフィール情報の更新頻度は？
2. データのバックアップは必要？
3. 情報の公開範囲の設定は？
```

要件が増えてきたら、`organize` コマンドで整理整頓：

```bash
You: organize

🔄 要件の再整理を開始します...

📋 再整理の結果:
==================================================
変更点:
- グループ化: プロフィール管理機能を集約
- 明確化: セキュリティ要件を具体化
- 優先順位: コア機能を Must Have に設定
```

仕上がり具合が気になってきたら `quality` コマンドで品質チェック：

```bash
You: quality

📊 要件の品質チェックを実行します...

要件: プロフィール情報の登録機能
総合スコア: 🟡 0.75

基本要素:
🟢 具体性: 0.90
🟡 測定可能性: 0.70
🟢 明確さ: 0.85

💡 改善提案:
- データ量の上限を明確にすることを検討
- 更新頻度の想定を追加
```

内容について多角的なレビューが欲しいときは `review` コマンドでLLMを使った複数人格によるレビュー結果が得られます：

```bash
You: review

👤 技術アーキテクト:
- 画像データの効率的な管理方法の検討が必要
- キャッシュ戦略の明確化を推奨

👤 UXデザイナー:
- プロフィール編集のユーザーフローを具体化
- 直感的な操作性の確保が重要
```

このように、RD-Assistant では：

1. 🌱 自然な会話から要件の種を見つけ
2. 🌿 AIとの対話で要件を育て
3. 🌳 コマンドで整理・改善を重ねる

というサイクルを楽しみながら回せます。

## 完璧を目指すのではなく、育てていく

RRD-Assistant の真骨頂は、「完璧な要件定義書を書く」ことではありません。

チャット感覚で始められ、いつでも整理でき、必要なときにレビューが受けられる。そんな気軽さの中で、要件定義の品質を徐々に高められることです。

## セットアップ

1. リポジトリのクローン
```bash
git clone https://github.com/hamatz/rd_assistant
cd rd_assistant
```

2. Poetry（パッケージマネージャ）のインストール（未インストールの場合）
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. 依存関係のインストール
```bash
poetry install
```

4. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集して、必要な認証情報を設定
```

## 使用方法

1. 対話型セッションの開始
```bash
poetry run python -m src.rd_assistant.main
```

## 環境変数について

- `AZURE_OPENAI_API_KEY`: Azure OpenAI ServiceのAPIキー
- `AZURE_OPENAI_API_BASE`: Azure OpenAI ServiceのエンドポイントURL
- `AZURE_OPENAI_API_VERSION`: Azure OpenAI ServiceのAPIバージョン
- `AZURE_OPENAI_DEPLOYMENT_NAME`: デプロイメント名

## ライセンス

本ツールは Apache License 2.0 にて提供されています。詳細につきましては LICENSE.txt をご確認ください