"""
Riot API関連の処理
"""
import asyncio
import requests
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from urllib.parse import quote

from config import (
    RIOT_API_KEY, API_TIMEOUT, REGION_MAPPING, QUEUE_ID_MAPPING,
    VERSIONS_URL, CHAMPIONS_URL_TEMPLATE, PROFILE_ICON_URL_TEMPLATE
)

class RiotAPI:
    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({"X-Riot-Token": RIOT_API_KEY})
        
        # チャンピオンデータキャッシュ
        self._champion_data = {}
        self._latest_version = ""
    
    def _log(self, level: str, message: str):
        """ログ出力"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [API-{level.upper()}] {message}")
    
    async def _api_request(self, url: str) -> Tuple[Optional[Dict], Optional[str]]:
        """API リクエストの共通処理"""
        try:
            response = await asyncio.to_thread(
                self._session.get, url, timeout=API_TIMEOUT
            )
            response.raise_for_status()
            return response.json(), None
            
        except requests.exceptions.Timeout:
            error_msg = f"APIリクエストがタイムアウトしました: {url}"
            self._log("error", error_msg)
            return None, error_msg
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None, None  # 404は「データなし」として正常に扱う
            if e.response.status_code == 403:
                error_msg = "APIキーが不正または無効です。 (403 Forbidden)"
            else:
                error_msg = f"API HTTPエラー: {e.response.status_code} - {url}"
            self._log("error", error_msg)
            return None, error_msg
            
        except requests.RequestException as e:
            error_msg = f"APIリクエストエラー: {e}"
            self._log("error", error_msg)
            return None, error_msg
    
    async def get_puuid(self, riot_id: str, region: str) -> Tuple[Optional[str], Optional[str]]:
        """Riot IDからPUUIDを取得"""
        if "#" not in riot_id:
            return None, "Riot IDは `GameName#TagLine` の形式で入力してください。"
        
        game_name, tag_line = riot_id.split("#", 1)
        continental_routing = REGION_MAPPING.get(region, {}).get("continental")
        
        if not continental_routing:
            return None, f"無効な地域です: {region}"
        
        api_url = (f"https://{continental_routing}.api.riotgames.com"
                  f"/riot/account/v1/accounts/by-riot-id/{quote(game_name)}/{tag_line}")
        
        data, error = await self._api_request(api_url)
        if error:
            return None, error
        if data:
            return data["puuid"], None
        
        return None, "指定されたRiot IDのプレイヤーが見つかりませんでした。"
    
    async def get_active_game(self, puuid: str, region: str) -> Optional[Dict[str, Any]]:
        """アクティブゲーム情報を取得"""
        platform_routing = REGION_MAPPING.get(region, {}).get("platform")
        if not platform_routing:
            return None
        
        api_url = (f"https://{platform_routing}.api.riotgames.com"
                  f"/lol/spectator/v5/active-games/by-summoner/{puuid}")
        
        data, error = await self._api_request(api_url)
        if error:
            self._log("error", f"試合情報取得失敗 (PUUID: {puuid}): {error}")
        
        return data
    
    async def get_match_details(self, match_id: str, region: str) -> Optional[Dict[str, Any]]:
        """試合詳細情報を取得"""
        continental_routing = REGION_MAPPING.get(region, {}).get("continental")
        if not continental_routing:
            return None
        
        api_url = (f"https://{continental_routing}.api.riotgames.com"
                  f"/lol/match/v5/matches/{match_id}")
        
        data, error = await self._api_request(api_url)
        if error:
            self._log("error", f"試合結果取得失敗 (Match ID: {match_id}): {error}")
        
        return data
    
    async def fetch_champion_data(self) -> bool:
        """チャンピオンデータを取得・更新"""
        try:
            # 最新バージョン取得
            response = await asyncio.to_thread(
                requests.get, VERSIONS_URL, timeout=API_TIMEOUT
            )
            response.raise_for_status()
            self._latest_version = response.json()[0]
            
            # チャンピオンデータ取得
            champions_url = CHAMPIONS_URL_TEMPLATE.format(version=self._latest_version)
            response = await asyncio.to_thread(
                requests.get, champions_url, timeout=API_TIMEOUT
            )
            response.raise_for_status()
            
            champion_json = response.json()
            self._champion_data = {
                int(info["key"]): info["name"] 
                for champ, info in champion_json["data"].items()
            }
            
            self._log("info", f"チャンピオンデータをロードしました。(バージョン: {self._latest_version})")
            return True
            
        except requests.RequestException as e:
            self._log("error", f"チャンピオンデータの取得に失敗: {e}")
            return False
    
    def get_champion_name(self, champion_id: int) -> str:
        """チャンピオンIDから名前を取得"""
        return self._champion_data.get(champion_id, "不明なチャンピオン")
    
    def get_game_mode_name_jp(self, game_info: Dict[str, Any]) -> str:
        """ゲーム情報から日本語モード名を取得"""
        queue_id = game_info.get("gameQueueConfigId")
        return QUEUE_ID_MAPPING.get(queue_id, game_info.get("gameMode", "不明なモード"))
    
    def get_profile_icon_url(self, icon_id: int) -> str:
        """プロフィールアイコンURLを取得"""
        return PROFILE_ICON_URL_TEMPLATE.format(
            version=self._latest_version, icon_id=icon_id
        )
    
    @property
    def latest_version(self) -> str:
        """最新バージョンを取得"""
        return self._latest_version
    
    @property
    def champion_data(self) -> Dict[int, str]:
        """チャンピオンデータを取得"""
        return self._champion_data.copy()

# グローバルインスタンス
riot_api = RiotAPI()
