import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv(dotenv_path=".env.example")

# Discord & Riot API 設定
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

# データベース設定
DB_FILE = "db.json"

# タスク実行間隔 (秒)
NEW_GAME_CHECK_INTERVAL = 60
FINISHED_GAME_CHECK_INTERVAL = 180
COMMAND_PROCESSOR_INTERVAL = 1

# API設定
API_TIMEOUT = 10
API_CALL_INTERVAL_NEW_GAME = 2
API_CALL_INTERVAL_FINISHED_GAME = 5

# Riot API 地域マッピング
REGION_MAPPING = {
    "BR1": {"platform": "BR1", "continental": "AMERICAS"},
    "EUN1": {"platform": "EUN1", "continental": "EUROPE"},
    "EUW1": {"platform": "EUW1", "continental": "EUROPE"},
    "JP1": {"platform": "JP1", "continental": "ASIA"},
    "KR": {"platform": "KR", "continental": "ASIA"},
    "LA1": {"platform": "LA1", "continental": "AMERICAS"},
    "LA2": {"platform": "LA2", "continental": "AMERICAS"},
    "NA1": {"platform": "NA1", "continental": "AMERICAS"},
    "OC1": {"platform": "OC1", "continental": "SEA"},
    "TR1": {"platform": "TR1", "continental": "EUROPE"},
    "RU": {"platform": "RU", "continental": "EUROPE"},
    "PH2": {"platform": "PH2", "continental": "SEA"},
    "SG2": {"platform": "SG2", "continental": "SEA"},
    "TH2": {"platform": "TH2", "continental": "SEA"},
    "TW2": {"platform": "TW2", "continental": "SEA"},
    "VN2": {"platform": "VN2", "continental": "SEA"},
}

# キューID マッピング
QUEUE_ID_MAPPING = {
    400: "ノーマル (ドラフト)",
    420: "ランク (ソロ/デュオ)",
    430: "ノーマル (ブラインド)",
    440: "ランク (フレックス)",
    450: "ランダムミッド (ARAM)",
    700: "Clash",
    1700: "アリーナ",
    1900: "URF",
}

# DeepLoL 地域マッピング
DEEPLOL_REGION_MAP = {
    "JP1": "jp", "KR": "kr", "NA1": "na", "EUW1": "euw",
    "EUN1": "eune", "TR1": "tr", "BR1": "br", "LA1": "lan",
    "LA2": "las", "OC1": "oce", "RU": "ru", "PH2": "ph",
    "SG2": "sg", "TH2": "th", "TW2": "tw", "VN2": "vn"
}

# Data Dragon URLs
VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
CHAMPIONS_URL_TEMPLATE = "https://ddragon.leagueoflegends.com/cdn/{version}/data/ja_JP/champion.json"
PROFILE_ICON_URL_TEMPLATE = "https://ddragon.leagueoflegends.com/cdn/{version}/img/profileicon/{icon_id}.png"

# 設定値の検証
def validate_config():
    """必要な設定値が存在するかチェック"""
    missing = []
    if not DISCORD_TOKEN:
        missing.append("DISCORD_TOKEN")
    if not RIOT_API_KEY:
        missing.append("RIOT_API_KEY")
    
    if missing:
        raise ValueError(f"必要な環境変数が設定されていません: {', '.join(missing)}")
    
    return True
