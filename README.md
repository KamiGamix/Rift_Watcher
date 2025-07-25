# Rift Watcher
![image](https://github.com/user-attachments/assets/9fb6079e-9ef6-40c4-9557-890b51db5c5e)


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance Discord bot that notifies you when a registered League of Legends player starts a match, and automatically updates the message with the match results upon completion.

**[🇯🇵 日本語のドキュメントはこちら](#-日本語)**

---

### 🇬🇧 English

This bot provides a seamless way to track the matches of your favorite League of Legends players directly within your Discord server.

#### ✨ Key Features

- **Easy Registration**: Register players to monitor by their Riot ID and region using a simple slash command (`/summonerset`).
- **Automatic Match Detection**: The bot periodically checks for new matches from all registered players in the background.
- **Instant Notifications**: Sends a rich embed message to a designated channel the moment a new match starts.
- **Live Game Link**: The notification title links directly to the player's live game on DeepLoL for easy spectating.
- **Automatic Result Updates**: Once the match is over, the initial notification message is **automatically edited** to show the match results (Win/Loss, KDA).
- **Detailed Match History**: The updated message title links to the detailed match history page on DeepLoL.
- **Robust & Reliable**: Built with asynchronous processing to handle API communications without blocking the bot. Player and match data are stored persistently.

#### 🔧 Setup Guide

1.  **Prerequisites**:
    -   Python 3.10 or higher
    -   A Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
    -   A Riot Games API Key ([Riot Developer Portal](https://developer.riotgames.com/))

2.  **Clone the Repository**:
    ```bash
    git clone https://github.com/KamiGamix/Rift_Watcher.git
    cd https://github.com/KamiGamix/Rift_Watcher.git
    ```

3.  **Install Dependencies**:
    It is recommended to use a virtual environment.
    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file in the project root by copying the example file.
    ```bash
    cp .env.example .env
    ```
    Now, open the `.env` file and fill in your tokens.
    ```ini
    DISCORD_TOKEN="Your_Discord_Bot_Token_Here"
    RIOT_API_KEY="Your_Riot_API_Key_Here"
    ```

5.  **Run the Bot**:
    ```bash
    python main.py
    ```
    The bot should now be online and ready to accept commands.

---

### 📜 Command Reference

| Command             | Description                                       | Arguments                       | Example                                  |
| ------------------- | ------------------------------------------------- | ------------------------------- | ---------------------------------------- |
| `/summonerset`      | Registers or updates a summoner to monitor.       | `riot_id`, `region`             | `/summonerset riot_id:Faker#KR1 region:KR` |
| `/summonerremove`   | Removes a summoner from the monitoring list.      | `riot_id` (with autocomplete)   | `/summonerremove riot_id:Faker#KR1`      |

---

### 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
---

## 🇯🇵 日本語

指定したLeague of Legendsプレイヤーが試合を開始した際にDiscordへ通知し、試合終了後には自動で対戦結果に更新する、高機能なボットです。

#### ✨ 主な機能

- **簡単なプレイヤー登録**: スラッシュコマンド (`/summonerset`) を使うだけで、Riot IDと地域を指定して監視対象プレイヤーを登録できます。
- **試合の自動検知**: 登録された全プレイヤーの試合状況をバックグラウンドで定期的にチェックします。
- **即時通知**: 新しい試合が始まった瞬間、指定されたチャンネルにリッチな埋め込みメッセージを送信します。
- **観戦用リンク**: 通知メッセージのタイトルは、DeepLoLの観戦ページにリンクしており、すぐに試合を観戦できます。
- **結果の自動更新**: 試合が終了すると、最初の通知メッセージが**自動的に編集**され、試合結果（勝利/敗北、KDA）に置き換わります。
- **詳細な戦績**: 更新後のメッセージは、DeepLoLの詳細な試合履歴ページにリンクします。
- **堅牢・高信頼性**: API通信などは非同期で処理されるため、ボットの応答が遅延しません。プレイヤーや試合のデータは永続的に保存されます。

#### 🔧 セットアップガイド

1.  **必要なもの**:
    -   Python 3.10 以上
    -   Discordボットトークン ([Discord Developer Portal](https://discord.com/developers/applications))
    -   Riot Games APIキー ([Riot Developer Portal](https://developer.riotgames.com/))

2.  **リポジトリをクローン**:
    ```bash
    git clone https://github.com/KamiGamix/Rift_Watcher.git
    cd https://github.com/KamiGamix/Rift_Watcher.git
    ```

3.  **依存ライブラリをインストール**:
    仮想環境の利用を推奨します。
    ```bash
    # Windowsの場合
    python -m venv venv
    .\venv\Scripts\activate
    # macOS/Linuxの場合
    python3 -m venv venv
    source venv/bin/activate
    
    pip install -r requirements.txt
    ```

4.  **環境変数の設定**:
    サンプルファイルをコピーして `.env` ファイルを作成します。
    ```bash
    cp .env.example .env
    ```
    作成した `.env` ファイルを開き、あなたのトークンを記述します。
    ```ini
    DISCORD_TOKEN="ここにあなたのDiscordボットトークン"
    RIOT_API_KEY="ここにあなたのRiot APIキー"
    ```

5.  **ボットを起動**:
    ```bash
    python main.py
    ```
    ボットがオンラインになり、コマンドを受け付けられる状態になります。

---

### 📜 コマンドリファレンス

| コマンド            | 説明                                      | 引数                            | 実行例                                   |
| ------------------- | ----------------------------------------- | ------------------------------- | ---------------------------------------- |
| `/summonerset`      | 監視対象のサモナーを登録・更新します。    | `riot_id`, `region`             | `/summonerset riot_id:Faker#KR1 region:KR` |
| `/summonerremove`   | 監視リストからサモナーを削除します。      | `riot_id` (入力補完あり)        | `/summonerremove riot_id:Faker#KR1`      |

---

### 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルをご覧ください。
