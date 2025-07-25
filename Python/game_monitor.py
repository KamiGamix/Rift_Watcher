import discord
from datetime import datetime
from discord_helpers import create_game_start_embed, create_match_result_embed

class GameMonitor:
    def __init__(self, discord_client, database, riot_api):
        self.client = discord_client
        self.db = database
        self.riot_api = riot_api
    
    def _log(self, level: str, message: str):
        """ログ出力"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [MONITOR-{level.upper()}] {message}")
    
    async def check_and_notify_single_summoner(self, summoner):
        """単一サモナーのチェックと通知"""
        puuid, riot_id, region = summoner["puuid"], summoner["riot_id"], summoner["region"]
        self._log("check", f"チェック対象: {riot_id}")
        
        game_info = await self.riot_api.get_active_game(puuid, region)
        if not game_info:
            self._log("check", f"-> {riot_id} は現在試合中ではありません。")
            return
        
        game_id = str(game_info["gameId"])
        self._log("check", f"-> {riot_id} は試合中です (Game ID: {game_id})")
        
        if self.db.is_game_notified(puuid, game_id):
            self._log("check", f"-> この試合は既に通知済みです。")
            return
        
        self._log("notify", f"-> 新しい試合を検知！通知を試みます...")
        
        try:
            channel = self.client.get_channel(summoner["channel_id"])
            if not channel:
                self._log("error", f"チャンネルが見つかりません (ID: {summoner['channel_id']})")
                return
            
            participant_info = next(
                (p for p in game_info["participants"] if p["puuid"] == puuid), None
            )
            if not participant_info:
                self._log("error", "試合情報内にプレイヤーが見つかりませんでした。")
                return
            
            embed = create_game_start_embed(riot_id, region, game_info, participant_info, self.riot_api)
            message = await channel.send(embed=embed)
            
            self._log("notify", f"-> Discordへの通知に成功: #{channel.name} (Message ID: {message.id})")
            
            # データベース更新
            self.db.set_game_notified(puuid, game_id)
            self.db.add_tracked_game({
                "puuid": puuid,
                "match_id": f"{region.upper()}_{game_id}",
                "region": region,
                "channel_id": channel.id,
                "message_id": message.id,
                "riot_id": riot_id
            })
            
        except discord.errors.Forbidden:
            self._log("error", "Discordへの投稿権限がありません！")
        except Exception as e:
            self._log("error", f"通知処理中に予期せぬエラーが発生: {e}")
    
    async def check_and_update_finished_game(self, game):
        """終了した試合のチェックと更新"""
        match_details = await self.riot_api.get_match_details(game["match_id"], game["region"])
        if not match_details:
            return
        
        self._log("notify", f"-> 試合終了検知: {game['match_id']}")
        
        try:
            info = match_details.get("info", {})
            participant_info = next(
                (p for p in info.get("participants", []) if p["puuid"] == game["puuid"]), None
            )
            
            if not participant_info:
                self._log("error", f"結果更新エラー: 試合結果内にプレイヤーが見つかりませんでした。Match ID: {game['match_id']}")
                return
            
            channel = self.client.get_channel(game["channel_id"])
            if not channel:
                self._log("error", f"結果更新エラー: チャンネル {game['channel_id']} が見つかりません。")
                self.db.remove_tracked_game(game)
                return
            
            message = await channel.fetch_message(game["message_id"])
            new_embed = create_match_result_embed(game, info, participant_info, self.riot_api)
            await message.edit(embed=new_embed)
            
            self._log("notify", f"-> メッセージを試合結果に更新しました (Message ID: {message.id})")
            self.db.remove_tracked_game(game)
            
        except discord.NotFound:
            self._log("error", f"結果更新エラー: メッセージ {game['message_id']} が削除されていました。追跡を中止します。")
            self.db.remove_tracked_game(game)
        except Exception as e:
            self._log("error", f"結果更新中に予期せぬエラー: {e}")
