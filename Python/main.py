"""
LoL Discord Bot - メインエントリーポイント
"""
import asyncio
import sys
from datetime import datetime

from config import validate_config, DISCORD_TOKEN, RIOT_API_KEY
from database import db
from riot_api import riot_api
from bot import bot

def log_message(level: str, message: str):
    """ログ出力"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level.upper()}] {message}")

async def initialize_application():
    """アプリケーションの初期化"""
    try:
        log_message("system", "アプリケーションを初期化しています...")
        
        # 設定値の検証
        validate_config()
        log_message("system", "設定値の検証完了")
        
        # データベースの初期化（自動で実行）
        log_message("system", f"データベース初期化完了 - 統計: {db.get_stats()}")
        
        # チャンピオンデータの取得
        success = await riot_api.fetch_champion_data()
        if not success:
            log_message("warning", "チャンピオンデータの取得に失敗しましたが、続行します")
        
        log_message("system", "初期化完了")
        return True
        
    except Exception as e:
        log_message("error", f"初期化エラー: {e}")
        return False

def main():
    """メイン実行関数"""
    log_message("system", "LoL Discord Bot を起動しています...")
    
    try:
        # 初期化とBot起動
        if not DISCORD_TOKEN or not RIOT_API_KEY:
            log_message("error", "DISCORD_TOKENまたはRIOT_API_KEYが設定されていません")
            log_message("error", ".envファイルを確認してください")
            sys.exit(1)
        
        # 非同期初期化は bot.py 内で実行
        bot.run(DISCORD_TOKEN)
        
    except KeyboardInterrupt:
        log_message("system", "キーボード割り込みによりBot を停止します")
    except Exception as e:
        log_message("error", f"予期せぬエラーが発生しました: {e}")
        sys.exit(1)
    finally:
        log_message("system", "Bot を終了しました")

if __name__ == "__main__":
    main()
