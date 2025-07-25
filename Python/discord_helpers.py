import discord
from urllib.parse import quote
from config import DEEPLOL_REGION_MAP

def create_game_start_embed(riot_id, region, game_info, participant_info, riot_api):
    """ゲーム開始通知のEmbed作成"""
    riot_id_encoded = quote(riot_id.replace("#", "-"))
    deeplol_region = DEEPLOL_REGION_MAP.get(region, region.lower().rstrip('1234567890'))
    deeplol_url = f"https://www.deeplol.gg/summoner/{deeplol_region}/{riot_id_encoded}/ingame"
    
    embed = discord.Embed(
        title=f"⚔️ {riot_id} が試合を開始しました！",
        url=deeplol_url,
        description="`タイトルをクリックして試合を観戦`",
        color=discord.Color.blue()
    )
    
    profile_icon_id = participant_info["profileIconId"]
    icon_url = riot_api.get_profile_icon_url(profile_icon_id)
    embed.set_thumbnail(url=icon_url)
    
    embed.add_field(
        name="ゲームモード", 
        value=riot_api.get_game_mode_name_jp(game_info), 
        inline=True
    )
    embed.add_field(
        name="チャンピオン", 
        value=riot_api.get_champion_name(participant_info["championId"]), 
        inline=True
    )
    
    embed.set_footer(text="試合開始通知")
    embed.timestamp = discord.utils.utcnow()
    
    return embed

def create_match_result_embed(game_track_info, match_info, participant_info, riot_api):
    """試合結果のEmbed作成"""
    result = "勝利" if participant_info.get("win") else "敗北"
    color = discord.Color.green() if result == "勝利" else discord.Color.red()
    
    riot_id_encoded = quote(game_track_info['riot_id'].replace("#", "-"))
    deeplol_region = DEEPLOL_REGION_MAP.get(
        game_track_info['region'], 
        game_track_info['region'].lower().rstrip('1234567890')
    )
    match_url = f"https://www.deeplol.gg/summoner/{deeplol_region}/{riot_id_encoded}/matches/{game_track_info['match_id']}"
    
    embed = discord.Embed(
        title=f"{game_track_info['riot_id']} の試合が終了しました",
        url=match_url,
        description="`タイトルをクリックして試合結果を確認`",
        color=color
    )
    
    profile_icon_id = participant_info.get("profileIcon", 0)
    icon_url = riot_api.get_profile_icon_url(profile_icon_id)
    embed.set_thumbnail(url=icon_url)
    
    embed.add_field(
        name="ゲームモード", 
        value=riot_api.get_game_mode_name_jp({"gameQueueConfigId": match_info.get("queueId")}), 
        inline=True
    )
    embed.add_field(
        name="チャンピオン", 
        value=riot_api.get_champion_name(participant_info.get("championId")), 
        inline=True
    )
    embed.add_field(name="\\u200b", value="\\u200b", inline=True)
    
    embed.add_field(name="結果", value=result, inline=True)
    embed.add_field(
        name="KDA", 
        value=f"{participant_info.get('kills', 0)}/{participant_info.get('deaths', 0)}/{participant_info.get('assists', 0)}", 
        inline=True
    )
    embed.add_field(name="\\u200b", value="\\u200b", inline=True)
    
    embed.set_footer(text="試合結果")
    embed.timestamp = discord.utils.utcnow()
    
    return embed
