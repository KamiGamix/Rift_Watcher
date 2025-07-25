import discord
from discord.ext import tasks
import os
import json
import requests
from dotenv import load_dotenv
import asyncio
from datetime import datetime
from urllib.parse import quote

# --- CONFIGURATION & CONSTANTS (Refactored: 設定値の集約) ---
# .envファイルから環境変数を読み込む
load_dotenv(dotenv_path=".env.example")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

# データベースファイル名
DB_FILE = "db.json"

# タスクの実行間隔 (秒)
NEW_GAME_CHECK_INTERVAL = 60
FINISHED_GAME_CHECK_INTERVAL = 180
COMMAND_PROCESSOR_INTERVAL = 1

# APIリクエストのタイムアウト時間 (秒)
API_TIMEOUT = 10
# APIリクエスト間のスリープ時間 (秒)
API_CALL_INTERVAL_NEW_GAME = 2
API_CALL_INTERVAL_FINISHED_GAME = 5

# Riot APIとデータドラゴンに関する静的マッピングデータ
REGION_MAPPING = { "BR1": {"platform": "BR1", "continental": "AMERICAS"}, "EUN1": {"platform": "EUN1", "continental": "EUROPE"}, "EUW1": {"platform": "EUW1", "continental": "EUROPE"}, "JP1": {"platform": "JP1", "continental": "ASIA"}, "KR": {"platform": "KR", "continental": "ASIA"}, "LA1": {"platform": "LA1", "continental": "AMERICAS"}, "LA2": {"platform": "LA2", "continental": "AMERICAS"}, "NA1": {"platform": "NA1", "continental": "AMERICAS"}, "OC1": {"platform": "OC1", "continental": "SEA"}, "TR1": {"platform": "TR1", "continental": "EUROPE"}, "RU": {"platform": "RU", "continental": "EUROPE"}, "PH2": {"platform": "PH2", "continental": "SEA"}, "SG2": {"platform": "SG2", "continental": "SEA"}, "TH2": {"platform": "TH2", "continental": "SEA"}, "TW2": {"platform": "TW2", "continental": "SEA"}, "VN2": {"platform": "VN2", "continental": "SEA"}, }
QUEUE_ID_MAPPING = { 400: "ノーマル (ドラフト)", 420: "ランク (ソロ/デュオ)", 430: "ノーマル (ブラインド)", 440: "ランク (フレックス)", 450: "ランダムミッド (ARAM)", 700: "Clash", 1700: "アリーナ", 1900: "URF", }
DEEPLOL_REGION_MAP = { "JP1": "jp", "KR": "kr", "NA1": "na", "EUW1": "euw", "EUN1": "eune", "TR1": "tr", "BR1": "br", "LA1": "lan", "LA2": "las", "OC1": "oce", "RU": "ru", "PH2": "ph", "SG2": "sg", "TH2": "th", "TW2": "tw", "VN2": "vn" }

# --- GLOBAL STATE & SETUP ---
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

db = {}
champion_data = {}
latest_lol_version = ""
command_queue = asyncio.Queue()

# (Refactored: requests.Sessionの一元管理)
# TCP接続を再利用し、共通ヘッダーを保持することでAPI通信を効率化する
api_session = requests.Session()
api_session.headers.update({"X-Riot-Token": RIOT_API_KEY})

# --- LOGGING & DATABASE HELPERS ---
def log_message(prefix, message): print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{prefix.upper()}] {message}")

def load_db():
    global db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try: db = json.load(f)
            except json.JSONDecodeError: db = {}
    db.setdefault('summoners', []); db.setdefault('notified_games', {}); db.setdefault('tracked_games', [])
    log_message("system", f"データベースをロードしました。監視対象: {len(db['summoners'])}名, 追跡中の試合: {len(db['tracked_games'])}件")

def save_db():
    with open(DB_FILE, "w") as f: json.dump(db, f, indent=4)
    log_message("db", "データベースをファイルに保存しました。")

# --- DATA DRAGON & STATIC DATA ---
async def fetch_latest_champion_data():
    global champion_data, latest_lol_version
    try:
        versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        response = await asyncio.to_thread(requests.get, versions_url, timeout=API_TIMEOUT)
        response.raise_for_status(); latest_lol_version = response.json()[0]
        champions_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_lol_version}/data/ja_JP/champion.json"
        response = await asyncio.to_thread(requests.get, champions_url, timeout=API_TIMEOUT)
        response.raise_for_status()
        champion_data = {int(info["key"]): info["name"] for champ, info in response.json()["data"].items()}
        log_message("system", f"チャンピオンデータをロードしました。(バージョン: {latest_lol_version})")
    except requests.RequestException as e:
        log_message("error", f"チャンピオンデータの取得に失敗: {e}")
        champion_data = {}

def get_champion_name(champion_id): return champion_data.get(champion_id, "不明なチャンピオン")
def get_game_mode_name_jp(game_info): return QUEUE_ID_MAPPING.get(game_info.get("gameQueueConfigId"), game_info.get("gameMode", "不明なモード"))

# --- RIOT API HELPERS (Refactored: Session利用とエラーハンドリング強化) ---
async def _api_request(url):
    try:
        response = await asyncio.to_thread(api_session.get, url, timeout=API_TIMEOUT)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.Timeout:
        return None, f"APIリクエストがタイムアウトしました: {url}"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404: return None, None # 404は「データなし」として正常に扱う
        if e.response.status_code == 403: return None, f"APIキーが不正または無効です。 (403 Forbidden)"
        return None, f"API HTTPエラー: {e.response.status_code} - {url}"
    except requests.RequestException as e:
        return None, f"APIリクエストエラー: {e}"

async def get_puuid(riot_id, region):
    if "#" not in riot_id: return None, "Riot IDは `GameName#TagLine` の形式で入力してください。"
    game_name, tag_line = riot_id.split("#", 1)
    continental_routing = REGION_MAPPING.get(region, {}).get("continental")
    if not continental_routing: return None, f"無効な地域です: {region}"
    api_url = f"https://{continental_routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(game_name)}/{tag_line}"
    data, error = await _api_request(api_url)
    if error: return None, error
    if data: return data["puuid"], None
    return None, "指定されたRiot IDのプレイヤーが見つかりませんでした。"

async def get_active_game(puuid, region):
    platform_routing = REGION_MAPPING.get(region, {}).get("platform")
    if not platform_routing: return None
    api_url = f"https://{platform_routing}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
    data, error = await _api_request(api_url)
    if error: log_message("api error", f"試合情報取得失敗 (PUUID: {puuid}): {error}")
    return data

async def get_match_details(match_id, region):
    continental_routing = REGION_MAPPING.get(region, {}).get("continental")
    if not continental_routing: return None
    api_url = f"https://{continental_routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    data, error = await _api_request(api_url)
    if error: log_message("api error", f"試合結果取得失敗 (Match ID: {match_id}): {error}")
    return data

# --- DISCORD EMBED HELPERS (Refactored: Embed生成ロジックの分離) ---
def create_game_start_embed(riot_id, region, game_info, participant_info):
    riot_id_encoded = quote(riot_id.replace("#", "-"))
    deeplol_region = DEEPLOL_REGION_MAP.get(region, region.lower().rstrip('1234567890'))
    deeplol_url = f"https://www.deeplol.gg/summoner/{deeplol_region}/{riot_id_encoded}/ingame"
    embed = discord.Embed(title=f"⚔️ {riot_id} が試合を開始しました！", url=deeplol_url, description="`タイトルをクリックして試合を観戦`", color=discord.Color.blue())
    profile_icon_id = participant_info["profileIconId"]
    icon_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_lol_version}/img/profileicon/{profile_icon_id}.png"
    embed.set_thumbnail(url=icon_url)

    embed.add_field(name="ゲームモード", value=get_game_mode_name_jp(game_info), inline=True)
    embed.add_field(name="チャンピオン", value=get_champion_name(participant_info["championId"]), inline=True)
    embed.set_footer(text="試合開始通知"); embed.timestamp = discord.utils.utcnow()
    return embed

def create_match_result_embed(game_track_info, match_info, participant_info):
    result = "勝利" if participant_info.get("win") else "敗北"
    color = discord.Color.green() if result == "勝利" else discord.Color.red()
    riot_id_encoded = quote(game_track_info['riot_id'].replace("#", "-"))
    deeplol_region = DEEPLOL_REGION_MAP.get(game_track_info['region'], game_track_info['region'].lower().rstrip('1234567890'))
    match_url = f"https://www.deeplol.gg/summoner/{deeplol_region}/{riot_id_encoded}/matches/{game_track_info['match_id']}"
    embed = discord.Embed(title=f" {game_track_info['riot_id']} の試合が終了しました", url=match_url, description="`タイトルをクリックして試合結果を確認`", color=color)
    profile_icon_id = participant_info.get("profileIcon", 0) # APIからの取得キーが異なる場合があるため修正
    icon_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_lol_version}/img/profileicon/{profile_icon_id}.png"
    embed.set_thumbnail(url=icon_url)

    embed.add_field(name="ゲームモード", value=QUEUE_ID_MAPPING.get(match_info.get("queueId"), "不明"), inline=True)
    embed.add_field(name="チャンピオン", value=get_champion_name(participant_info.get("championId")), inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="結果", value=result, inline=True)
    embed.add_field(name="KDA", value=f"{participant_info.get('kills', 0)}/{participant_info.get('deaths', 0)}/{participant_info.get('assists', 0)}", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.set_footer(text="試合結果"); embed.timestamp = discord.utils.utcnow()
    return embed

# --- CORE APPLICATION LOGIC ---
async def check_and_notify_single_summoner(summoner):
    puuid, riot_id, region = summoner["puuid"], summoner["riot_id"], summoner["region"]
    log_message("check", f"チェック対象: {riot_id}")
    game_info = await get_active_game(puuid, region)
    if not game_info:
        log_message("check", f"-> {riot_id} は現在試合中ではありません。")
        return
    game_id = str(game_info["gameId"])
    log_message("check", f"-> {riot_id} は試合中です (Game ID: {game_id})")
    if db["notified_games"].get(puuid) == game_id:
        log_message("check", f"-> この試合は既に通知済みです。")
        return
    log_message("notify", f"-> 新しい試合を検知！通知を試みます...")
    try:
        channel = client.get_channel(summoner["channel_id"])
        if not channel:
            log_message("error", f"チャンネルが見つかりません (ID: {summoner['channel_id']})")
            return
        participant_info = next((p for p in game_info["participants"] if p["puuid"] == puuid), None)
        if not participant_info:
            log_message("error", "試合情報内にプレイヤーが見つかりませんでした。")
            return
        embed = create_game_start_embed(riot_id, region, game_info, participant_info)
        message = await channel.send(embed=embed)
        log_message("notify", f"-> Discordへの通知に成功: #{channel.name} (Message ID: {message.id})")
        db["notified_games"][puuid] = game_id
        db['tracked_games'].append({"puuid": puuid, "match_id": f"{region.upper()}_{game_id}", "region": region, "channel_id": channel.id, "message_id": message.id, "riot_id": riot_id})
        save_db()
    except discord.errors.Forbidden:
        log_message("error", "Discordへの投稿権限がありません！")
    except Exception as e:
        log_message("error", f"通知処理中に予期せぬエラーが発生: {e}")

# --- DISCORD EVENTS & TASKS ---
@client.event
async def on_ready():
    load_db()
    await fetch_latest_champion_data()
    await tree.sync()
    if not command_processor_loop.is_running(): command_processor_loop.start()
    if not check_new_games_loop.is_running(): check_new_games_loop.start()
    if not check_finished_games_loop.is_running(): check_finished_games_loop.start()
    log_message("system", f"{client.user}としてログインしました。")

@tasks.loop(seconds=COMMAND_PROCESSOR_INTERVAL)
async def command_processor_loop():
    task = await command_queue.get()
    interaction = task["interaction"]
    if task["type"] == "set":
        riot_id, region = task["riot_id"], task["region"]
        log_message("command_proc", f"/summonerset タスク処理開始 (riot_id: {riot_id})")
        puuid, error_message = await get_puuid(riot_id, region)
        if error_message:
            await interaction.edit_original_response(content=f"❌ エラー: {error_message}")
            return
        summoner_entry = next((s for s in db["summoners"] if s["riot_id"].lower() == riot_id.lower()), None)
        if summoner_entry:
            summoner_entry.update({"channel_id": interaction.channel_id, "region": region, "puuid": puuid})
            message = f"✅ サモナー `{riot_id}` の設定を更新しました。"
        else:
            summoner_entry = {"riot_id": riot_id, "puuid": puuid, "region": region, "channel_id": interaction.channel_id}
            db["summoners"].append(summoner_entry)
            message = f"✅ サモナー `{riot_id}` を新規登録しました。"
        save_db()
        await interaction.edit_original_response(content=message)
        log_message("command_proc", f"-> {riot_id} の即時チェックを開始。")
        await check_and_notify_single_summoner(summoner_entry)

@tasks.loop(seconds=NEW_GAME_CHECK_INTERVAL)
async def check_new_games_loop():
    if not db.get("summoners"): return
    log_message("loop", f"【開始チェック】(対象: {len(db['summoners'])}名)")
    for summoner in list(db["summoners"]):
        await check_and_notify_single_summoner(summoner)
        await asyncio.sleep(API_CALL_INTERVAL_NEW_GAME)

@tasks.loop(seconds=FINISHED_GAME_CHECK_INTERVAL)
async def check_finished_games_loop():
    if not db.get("tracked_games"): return
    log_message("loop", f"【終了チェック】(対象: {len(db['tracked_games'])}件)")
    for game in list(db["tracked_games"]):
        match_details = await get_match_details(game["match_id"], game["region"])
        if match_details:
            log_message("notify", f"-> 試合終了検知: {game['match_id']}")
            try:
                info = match_details.get("info", {})
                participant_info = next((p for p in info.get("participants", []) if p["puuid"] == game["puuid"]), None)
                if not participant_info:
                    log_message("error", f"結果更新エラー: 試合結果内にプレイヤーが見つかりませんでした。Match ID: {game['match_id']}")
                    continue # 次のゲームへ
                channel = client.get_channel(game["channel_id"])
                if not channel:
                    log_message("error", f"結果更新エラー: チャンネル {game['channel_id']} が見つかりません。")
                    db["tracked_games"].remove(game); save_db()
                    continue
                message = await channel.fetch_message(game["message_id"])
                new_embed = create_match_result_embed(game, info, participant_info)
                await message.edit(embed=new_embed)
                log_message("notify", f"-> メッセージを試合結果に更新しました (Message ID: {message.id})")
                db["tracked_games"].remove(game); save_db()
            except discord.NotFound:
                log_message("error", f"結果更新エラー: メッセージ {game['message_id']} が削除されていました。追跡を中止します。")
                db["tracked_games"].remove(game); save_db()
            except Exception as e:
                log_message("error", f"結果更新中に予期せぬエラー: {e}")
        await asyncio.sleep(API_CALL_INTERVAL_FINISHED_GAME)

@command_processor_loop.before_loop
@check_new_games_loop.before_loop
@check_finished_games_loop.before_loop
async def before_loops(): await client.wait_until_ready()

# --- DISCORD COMMANDS ---
@tree.command(name="summonerset", description="監視対象のサモナーを登録・更新します。")
@discord.app_commands.describe(riot_id="監視するRiot ID (例: Faker#KR1)", region=f"地域コード ({', '.join(REGION_MAPPING.keys())})")
@discord.app_commands.choices(region=[discord.app_commands.Choice(name=key, value=key) for key in REGION_MAPPING.keys()])
async def summoner_set(interaction: discord.Interaction, riot_id: str, region: str):
    await interaction.response.send_message("⏳ 登録処理をバックグラウンドで開始します。少々お待ちください...", ephemeral=True)
    await command_queue.put({"type": "set", "interaction": interaction, "riot_id": riot_id, "region": region})

async def summoner_remove_autocomplete(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:
    choices = [discord.app_commands.Choice(name=s["riot_id"], value=s["riot_id"])
               for s in db.get("summoners", [])
               if s["channel_id"] == interaction.channel_id and current.lower() in s["riot_id"].lower()]
    return choices[:25]

@tree.command(name="summonerremove", description="このチャンネルの監視リストからサモナーを削除します。")
@discord.app_commands.autocomplete(riot_id=summoner_remove_autocomplete)
@discord.app_commands.describe(riot_id="削除するRiot ID")
async def summoner_remove(interaction: discord.Interaction, riot_id: str):
    log_message("command", f"/summonerremove by {interaction.user} (riot_id: {riot_id})")
    s_to_remove = next((s for s in db.get("summoners", []) if s["riot_id"].lower() == riot_id.lower() and s["channel_id"] == interaction.channel_id), None)
    if s_to_remove:
        puuid_to_remove = s_to_remove.get("puuid")
        db["summoners"].remove(s_to_remove)
        if puuid_to_remove and puuid_to_remove in db.get("notified_games", {}):
            del db["notified_games"][puuid_to_remove]
        db["tracked_games"] = [game for game in db["tracked_games"] if game.get("puuid") != puuid_to_remove]
        save_db()
        log_message("db", f"サモナー {riot_id} を削除しました。")
        await interaction.response.send_message(f"サモナー `{riot_id}` を監視リストから削除しました。", ephemeral=True)
    else:
        await interaction.response.send_message(f"サモナー `{riot_id}` はこのチャンネルの監視リストに見つかりませんでした。", ephemeral=True)

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    if DISCORD_TOKEN and RIOT_API_KEY:
        client.run(DISCORD_TOKEN)
    else:
        log_message("system", "致命的エラー: DISCORD_TOKENまたはRIOT_API_KEYが.envファイルに設定されていません。")