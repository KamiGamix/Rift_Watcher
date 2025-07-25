import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import DB_FILE

class Database:
    def __init__(self):
        self._data = {}
        self._load()
    
    def _load(self):
        """データベースファイルを読み込み"""
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                self._log("データベースをロードしました")
            except json.JSONDecodeError as e:
                self._log(f"データベースファイルの読み込みに失敗: {e}")
                self._data = {}
        
        # デフォルト構造の初期化
        self._data.setdefault('summoners', [])
        self._data.setdefault('notified_games', {})
        self._data.setdefault('tracked_games', [])
        
        self._log(f"監視対象: {len(self._data['summoners'])}名, "
                 f"追跡中の試合: {len(self._data['tracked_games'])}件")
    
    def save(self):
        """データベースをファイルに保存"""
        try:
            # バックアップ作成
            if os.path.exists(DB_FILE):
                backup_name = f"{DB_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(DB_FILE, backup_name)
            
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
            
            self._log("データベースをファイルに保存しました")
        except Exception as e:
            self._log(f"データベース保存エラー: {e}")
            raise
    
    def _log(self, message: str):
        """ログ出力"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DB] {message}")
    
    # サモナー管理
    def get_summoners(self) -> List[Dict[str, Any]]:
        """全サモナー取得"""
        return self._data['summoners']
    
    def add_summoner(self, summoner_data: Dict[str, Any]) -> bool:
        """サモナー追加"""
        # 既存チェック
        existing = self.get_summoner_by_riot_id(summoner_data['riot_id'])
        if existing:
            # 更新
            existing.update(summoner_data)
            self._log(f"サモナー {summoner_data['riot_id']} を更新しました")
        else:
            # 新規追加
            self._data['summoners'].append(summoner_data)
            self._log(f"サモナー {summoner_data['riot_id']} を追加しました")
        
        self.save()
        return True
    
    def remove_summoner(self, riot_id: str, channel_id: int) -> bool:
        """サモナー削除"""
        summoner = next((s for s in self._data['summoners'] 
                        if s['riot_id'].lower() == riot_id.lower() 
                        and s['channel_id'] == channel_id), None)
        
        if summoner:
            puuid = summoner.get('puuid')
            self._data['summoners'].remove(summoner)
            
            # 関連データも削除
            if puuid and puuid in self._data['notified_games']:
                del self._data['notified_games'][puuid]
            
            self._data['tracked_games'] = [
                game for game in self._data['tracked_games'] 
                if game.get('puuid') != puuid
            ]
            
            self.save()
            self._log(f"サモナー {riot_id} を削除しました")
            return True
        
        return False
    
    def get_summoner_by_riot_id(self, riot_id: str) -> Optional[Dict[str, Any]]:
        """Riot IDでサモナー検索"""
        return next((s for s in self._data['summoners'] 
                    if s['riot_id'].lower() == riot_id.lower()), None)
    
    def get_summoners_by_channel(self, channel_id: int) -> List[Dict[str, Any]]:
        """チャンネルIDでサモナー検索"""
        return [s for s in self._data['summoners'] if s['channel_id'] == channel_id]
    
    # 通知管理
    def is_game_notified(self, puuid: str, game_id: str) -> bool:
        """ゲームが通知済みかチェック"""
        return self._data['notified_games'].get(puuid) == game_id
    
    def set_game_notified(self, puuid: str, game_id: str):
        """ゲームを通知済みに設定"""
        self._data['notified_games'][puuid] = game_id
        self.save()
    
    # 追跡ゲーム管理
    def get_tracked_games(self) -> List[Dict[str, Any]]:
        """追跡中ゲーム取得"""
        return self._data['tracked_games']
    
    def add_tracked_game(self, game_data: Dict[str, Any]):
        """追跡ゲーム追加"""
        self._data['tracked_games'].append(game_data)
        self.save()
    
    def remove_tracked_game(self, game_data: Dict[str, Any]):
        """追跡ゲーム削除"""
        if game_data in self._data['tracked_games']:
            self._data['tracked_games'].remove(game_data)
            self.save()
    
    # データベース管理
    def cleanup_old_data(self, days: int = 7):
        """古いデータのクリーンアップ"""
        # 古い追跡ゲームを削除（実装例）
        # 実際の使用では、タイムスタンプベースでの削除を実装
        pass
    
    def get_stats(self) -> Dict[str, int]:
        """統計情報取得"""
        return {
            'summoners_count': len(self._data['summoners']),
            'tracked_games_count': len(self._data['tracked_games']),
            'notified_games_count': len(self._data['notified_games'])
        }

# グローバルインスタンス
db = Database()
