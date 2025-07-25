"""
Discord Bot の本体
"""
import asyncio
import discord
from discord.ext import tasks
from datetime import datetime

from config import (
    NEW_GAME_CHECK_INTERVAL, FINISHED_GAME_CHECK_INTERVAL, 
    COMMAND_PROCESSOR_INTERVAL, REGION_MAPPING,
    API_CALL_INTERVAL_NEW_GAME, API_CALL_INTERVAL_FINISHED_GAME
)
from database import db
from riot_api import riot_api
from discord_helpers import create_game_start_embed, create_match_result_embed
from game_monitor import GameMonitor

class LoLBot:
    def __init__(self):
        # Discord クライアント設定
        intents = discord.Intents.default()
        self.client = discord.Client(intents=intents)
        self.tree = discord.app_commands.CommandTree(self.client)
        
        # コマンドキュー
        self.command_queue = asyncio.Queue()
        
        # ゲーム監視
        self.game_monitor = GameMonitor(self.client, db, riot_api)
        
        # イベントハンドラー登録
        self._setup_events()
        self._setup_commands()
    
    def _log(self, level: str, message: str):
        """ログ出力"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [BOT-{level.upper()}] {message}")
    
    def _setup_events(self):
        """イベントハンドラーの設定"""
        @self.client.event
        async def on_ready():
            await self._on_ready()
    
    async def _on_ready(self):
        """Bot起動時の処理"""
        self._log("system", f"{self.client.user} としてログインしました")
        
        # 初期化処理
        await riot_api.fetch_champion_data()
        await self.tree.sync()
        
        # タスクループ開始
        if not self.command_processor_loop.is_running():
            self.command_processor_loop.start()
        if not self.check_new_games_loop.is_running():
            self.check_new_games_loop.start()
        if not self.check_finished_games_loop.is_running():
            self.check_finished_games_loop.start()
        
        self._log("system", "Bot の初期化が完了しました")
    
    def _setup_commands(self):
        """スラッシュコマンドの設定"""
        
        @self.tree.command(name="summonerset", description="監視対象のサモナーを登録・更新します。")
        @discord.app_commands.describe(
            riot_id="監視するRiot ID (例: Faker#KR1)", 
            region=f"地域コード ({', '.join(REGION_MAPPING.keys())})"
        )
        @discord.app_commands.choices(
            region=[discord.app_commands.Choice(name=key, value=key) for key in REGION_MAPPING.keys()]
        )
        async def summoner_set(interaction: discord.Interaction, riot_id: str, region: str):
            await interaction.response.send_message(
                "⏳ 登録処理をバックグラウンドで開始します。少々お待ちください...", 
                ephemeral=True
            )
            await self.command_queue.put({
                "type": "set", 
                "interaction": interaction, 
                "riot_id": riot_id, 
                "region": region
            })
        
        async def summoner_remove_autocomplete(interaction: discord.Interaction, current: str):
            summoners = db.get_summoners_by_channel(interaction.channel_id)
            choices = [
                discord.app_commands.Choice(name=s["riot_id"], value=s["riot_id"])
                for s in summoners
                if current.lower() in s["riot_id"].lower()
            ]
            return choices[:25]
        
        @self.tree.command(name="summonerremove", description="このチャンネルの監視リストからサモナーを削除します。")
        @discord.app_commands.autocomplete(riot_id=summoner_remove_autocomplete)
        @discord.app_commands.describe(riot_id="削除するRiot ID")
        async def summoner_remove(interaction: discord.Interaction, riot_id: str):
            self._log("command", f"/summonerremove by {interaction.user} (riot_id: {riot_id})")
            
            success = db.remove_summoner(riot_id, interaction.channel_id)
            if success:
                message = f"✅ サモナー `{riot_id}` を監視リストから削除しました。"
            else:
                message = f"❌ サモナー `{riot_id}` はこのチャンネルの監視リストに見つかりませんでした。"
            
            await interaction.response.send_message(message, ephemeral=True)
        
        @self.tree.command(name="status", description="Bot の状態とサモナー一覧を表示します。")
        async def status(interaction: discord.Interaction):
            stats = db.get_stats()
            channel_summoners = db.get_summoners_by_channel(interaction.channel_id)
            
            embed = discord.Embed(
                title="🤖 Bot Status", 
                color=discord.Color.blue()
            )
            embed.add_field(
                name="グローバル統計", 
                value=f"監視対象: {stats['summoners_count']}名\n"
                      f"追跡中試合: {stats['tracked_games_count']}件", 
                inline=False
            )
            
            if channel_summoners:
                summoner_list = "\n".join([f"• {s['riot_id']} ({s['region']})" for s in channel_summoners])
                embed.add_field(
                    name=f"このチャンネルの監視対象 ({len(channel_summoners)}名)", 
                    value=summoner_list, 
                    inline=False
                )
            else:
                embed.add_field(
                    name="このチャンネルの監視対象", 
                    value="登録されていません", 
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @tasks.loop(seconds=COMMAND_PROCESSOR_INTERVAL)
    async def command_processor_loop(self):
        """コマンド処理ループ"""
        try:
            task = await asyncio.wait_for(self.command_queue.get(), timeout=0.1)
            await self._process_command(task)
        except asyncio.TimeoutError:
            pass  # キューが空の場合
    
    async def _process_command(self, task):
        """コマンド処理"""
        interaction = task["interaction"]
        
        if task["type"] == "set":
            riot_id, region = task["riot_id"], task["region"]
            self._log("command_proc", f"/summonerset 処理開始 (riot_id: {riot_id})")
            
            puuid, error_message = await riot_api.get_puuid(riot_id, region)
            if error_message:
                await interaction.edit_original_response(content=f"❌ エラー: {error_message}")
                return
            
            summoner_data = {
                "riot_id": riot_id,
                "puuid": puuid,
                "region": region,
                "channel_id": interaction.channel_id
            }
            
            existing = db.get_summoner_by_riot_id(riot_id)
            if existing:
                message = f"✅ サモナー `{riot_id}` の設定を更新しました。"
            else:
                message = f"✅ サモナー `{riot_id}` を新規登録しました。"
            
            db.add_summoner(summoner_data)
            await interaction.edit_original_response(content=message)
            
            # 即時チェック
            self._log("command_proc", f"-> {riot_id} の即時チェックを開始")
            await self.game_monitor.check_and_notify_single_summoner(summoner_data)
    
    @tasks.loop(seconds=NEW_GAME_CHECK_INTERVAL)
    async def check_new_games_loop(self):
        """新しい試合のチェック"""
        summoners = db.get_summoners()
        if not summoners:
            return
        
        self._log("loop", f"【開始チェック】(対象: {len(summoners)}名)")
        
        for summoner in summoners:
            await self.game_monitor.check_and_notify_single_summoner(summoner)
            await asyncio.sleep(API_CALL_INTERVAL_NEW_GAME)
    
    @tasks.loop(seconds=FINISHED_GAME_CHECK_INTERVAL)
    async def check_finished_games_loop(self):
        """終了した試合のチェック"""
        tracked_games = db.get_tracked_games()
        if not tracked_games:
            return
        
        self._log("loop", f"【終了チェック】(対象: {len(tracked_games)}件)")
        
        for game in tracked_games.copy():  # コピーして安全に反復
            await self.game_monitor.check_and_update_finished_game(game)
            await asyncio.sleep(API_CALL_INTERVAL_FINISHED_GAME)
    
    @command_processor_loop.before_loop
    @check_new_games_loop.before_loop
    @check_finished_games_loop.before_loop
    async def before_loops(self):
        """ループ開始前の待機"""
        await self.client.wait_until_ready()
    
    def run(self, token: str):
        """Bot実行"""
        self.client.run(token)

# グローバルインスタンス
bot = LoLBot()
