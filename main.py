# main.py

import os
import random
import discord
from flask import Flask
import threading
import asyncio

# -----------------------------------------------------------------------------
# Flask (Render用Webサーバー)
# -----------------------------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def hello():
    """Renderが正常に起動しているか確認するためのルート"""
    return "Discord Bot is active now"

# GunicornがWebサーバーを起動するため、run_web関数は不要になります。

# -----------------------------------------------------------------------------
# Discordボットの設定
# -----------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

SHOT_TYPE = (
    # ... (この部分は変更なし) ...
)

STICKER = (
    # ... (この部分は変更なし) ...
)

def get_random_shot():
    # ... (この部分は変更なし) ...

# -----------------------------------------------------------------------------
# Discordイベント
# -----------------------------------------------------------------------------
@client.event
async def on_ready():
    # ... (この部分は変更なし) ...

@client.event
async def on_message(message):
    if message.author == client.user or message.author.bot:
        return
    if (client.user.mentioned_in(message) or any(keyword in message.content for keyword in ["本日の機体", "今日の機体", "きょうのきたい", "ほんじつのきたい", "イッツルナティックターイム！"])):
        await message.channel.send(get_random_shot())
        return
    if "x.com" in message.content:
        await message.channel.send(message.content.replace("x.com", "vxtwitter.com"))
        return
    if "www.pixiv.net" in message.content:
        await message.channel.send(message.content.replace("www.pixiv.net", "www.phixiv.net"))
        return
    if any(keyword in message.content for keyword in ["にゃ～ん", "にゃーん"]):
        await message.channel.send("にゃ～ん")
        return
    if any(keyword in message.content for keyword in ["説明!", "せつめい!"]):
        await message.channel.send("今日の機体、本日の機体 またはメンションで機体出します")
        return
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ソースコードのURLをGitHubリポジトリに変更
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    if any(keyword in message.content for keyword in ["ソースコード", "そーす"]):
        # ↓↓↓ あなたのGitHubリポジトリのURLに書き換えてください
        await message.channel.send("https://github.com/Kakeyouyou33554432/dis_test")
        return
    if any(keyword in message.content for keyword in ["スタンプ", "すたんぷ"]):
        await message.channel.send(random.choice(STICKER))
        return
    if any(s in message.content for s in STICKER) or "💤" in message.content:
        await message.channel.send(random.choice(STICKER))
        return

# -----------------------------------------------------------------------------
# 並列起動
# -----------------------------------------------------------------------------
def run_bot():
    bot_token = os.environ.get("DISCORD_BOT_TOKEN")
    if not bot_token:
        print("DISCORD_BOT_TOKENが設定されていません。")
        return
    # asyncioのイベントループを適切に設定
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # client.start()はブロッキングなので、loop.run_until_completeは不要
    # client.run(bot_token) の方が一般的
    loop.create_task(client.start(bot_token))
    loop.run_forever()


# Gunicornから起動されるため、このファイルが直接実行されることはない
# Discordボットは別のスレッドで起動する
bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()
