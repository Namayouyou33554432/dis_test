import os
import random
import discord
from flask import Flask
import threading
import asyncio
import re
import io
import json
import aiohttp
import traceback
from datetime import datetime, timedelta, timezone

# -----------------------------------------------------------------------------
# Flask (Render用Webサーバー)
# -----------------------------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def hello():
    """Renderが正常に起動しているか確認するためのルート"""
    return "Discord Bot is active now"

# -----------------------------------------------------------------------------
# Discordボットの設定
# -----------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)

# ユーザーごとの送信先設定を記憶する辞書
# { user_id: "dm" or "channel" }
# デフォルトは 'channel' (DMオフ)
user_settings = {}

# (SHOT_TYPE, STICKER, GACHA_* 定数は変更ないため省略)
SHOT_TYPE = (
    (4, "紅霊夢A", "紅霊夢B", "紅魔理沙A", "紅魔理沙B"),
    (6, "妖霊夢A", "妖霊夢B", "妖魔理沙A", "妖魔理沙B", "妖咲夜A", "妖咲夜B"),
    (12, "永結界", "永幽冥", "永詠唱", "永紅魔", "永霊夢", "永紫", "永妖夢", "永幽々子", "永魔理沙", "永アリス", "永咲夜", "永レミリア"),
    (6, "風霊夢A", "風霊夢B", "風霊夢C", "風魔理沙A", "風魔理沙B", "風魔理沙C"),
    (6, "地霊夢A", "地霊夢B", "地霊夢C", "地魔理沙A", "地魔理沙B", "地魔理沙C"),
    (6, "星霊夢A", "星霊夢B", "星魔理沙A", "星魔理沙B", "星早苗A", "星早苗B"),
    (4, "神霊夢", "神魔理沙", "神早苗", "神妖夢"),
    (6, "輝霊夢A", "輝霊夢B", "輝魔理沙A", "輝魔理沙B", "輝咲夜A", "輝咲夜B"),
    (4, "紺霊夢", "紺魔理沙", "紺早苗", "紺鈴仙"),
    (16, "春春", "春夏", "春秋", "春冬", "夏春", "夏夏", "夏秋", "夏冬", "秋春", "秋夏", "秋秋", "秋冬", "冬春", "冬夏", "冬秋", "冬冬"),
    (9, "霊夢W", "霊夢E", "霊夢O", "魔理沙W", "魔理沙E", "魔理沙O", "妖夢W", "妖夢E", "妖夢O"),
    (4, "虹霊夢", "虹魔理沙", "虹咲夜", "虹早苗"),
)

STICKER = (
    "<:kazusa:1318960518215766117>", "<:plana1:1318960569822351370>", "<:plana:1318960622268059728>",
    "<:nyny:1318960704249663498>", "<:plana2:1318964188537815150>", "<:usio:1318964272038019132>",
    "<:chiaki:1318964308628996106>",
)

GACHA_TRIGGER = "<:img:1332781427498029106>"
GACHA_STAR_1 = ("<:JYUNYA:921397676166234162>", "<:maiahi:855369574819168266>", "<:emoji_33:901741259260039239>")
GACHA_STAR_2 = ("<:beerjunya:859283357841489950>",)
GACHA_STAR_3 = ("<:rainbowjunya2:930782219490983937>",)
GACHA_ITEMS = [GACHA_STAR_1, GACHA_STAR_2, GACHA_STAR_3, STICKER]
GACHA_WEIGHTS_NORMAL = [78.5, 18.5, 2.3, 0.7]
GACHA_WEIGHTS_GUARANTEED = [0, 18.5 + 78.5, 2.3, 0.7]

# -----------------------------------------------------------------------------
# UIコンポーネント
# -----------------------------------------------------------------------------
class DeleteButtonView(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="削除", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await interaction.message.delete()
        except discord.HTTPException as e:
            print(f"Failed to delete message: {e}")

# -----------------------------------------------------------------------------
# ヘルパー関数
# -----------------------------------------------------------------------------
async def download_and_send_images(destination, image_url_groups, fallback_channel, mention_user):
    if not image_url_groups:
        return False

    files_to_send = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': 'https://www.pixiv.net/'
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            MAX_FILE_SIZE = 24 * 1024 * 1024
            for i, url_group in enumerate(image_url_groups):
                download_success = False
                for img_url in url_group:
                    try:
                        async with session.get(img_url) as img_resp:
                            if img_resp.status == 200:
                                image_data = await img_resp.read()
                                if len(image_data) > MAX_FILE_SIZE:
                                    await fallback_channel.send(f"画像 {i+1} はサイズが大きすぎるため、送信できません。({len(image_data) / 1024 / 1024:.2f}MB)")
                                    download_success = True
                                    break
                                
                                filename = os.path.basename(img_url.split('?')[0])
                                files_to_send.append(discord.File(io.BytesIO(image_data), filename=filename))
                                download_success = True
                                break
                    except Exception as dl_error:
                        print(f"Attempt failed for {img_url}: {dl_error}")
                        continue
                
                if not download_success:
                    await fallback_channel.send(f"画像 {i+1} のダウンロードに全ての拡張子で失敗しました。")
    except Exception as e:
        print(f"画像ダウンロード中に予期せぬエラーが発生しました: {e}")
        traceback.print_exc()
        await fallback_channel.send(f"画像ダウンロード中に予期せぬエラーが発生しました: `{type(e).__name__}`")
        return False

    if not files_to_send:
        if any(image_url_groups):
             return True
        return False

    is_dm_target = isinstance(destination, (discord.User, discord.Member))

    try:
        view = DeleteButtonView() if is_dm_target else None
        for i in range(0, len(files_to_send), 10):
            chunk = files_to_send[i:i+10]
            await destination.send(files=chunk, view=view)
        print(f"Sent {len(files_to_send)} images to {destination}.")
        return True
    except discord.Forbidden:
        if is_dm_target:
            print(f"Failed to send DM to {destination}. Sending to channel instead.")
            await fallback_channel.send(
                f"{mention_user.mention} DMに画像を送信できませんでした。プライバシー設定を確認してください。"
            )
        return False
    except Exception as e:
        print(f"An error occurred while sending files: {e}")
        traceback.print_exc()
        await fallback_channel.send(f"画像の送信中に予期せぬエラーが発生しました: `{type(e).__name__}`")
        return False

# -----------------------------------------------------------------------------
# メインの処理関数
# -----------------------------------------------------------------------------
async def process_media_link(message, url_type):
    image_url_groups = []
    
    try:
        async with message.channel.typing():
            if url_type == 'twitter':
                match = re.search(r'https?://(?:www\.)?(?:x|twitter)\.com/(\w+/status/\d+)', message.content)
                if not match: return
                
                api_url = f"https://api.fxtwitter.com/{match.group(1)}"
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(api_url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            media_list = data.get('tweet', {}).get('media', {}).get('all', [])
                            for media in media_list:
                                image_url_groups.append([media['url']])
            
            elif url_type == 'pixiv':
                match = re.search(r'https?://(?:www\.)?pixiv\.net/(?:en/)?artworks/(\d+)', message.content)
                if not match: return
                artwork_id = match.group(1)

                api_url = f"https://www.phixiv.net/api/info?id={artwork_id}"
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
                
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(api_url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            
                            proxy_urls = data.get("image_proxy_urls", [])
                            if not proxy_urls:
                                await message.channel.send("APIから画像URLが見つかりませんでした。")
                                return
                            
                            pattern = re.compile(r'/img/(\d{4}/\d{2}/\d{2}/\d{2}/\d{2}/\d{2})/(\d+)_p(\d+)')

                            for proxy_url in proxy_urls:
                                url_match = pattern.search(proxy_url)
                                if url_match:
                                    date_path = url_match.group(1)
                                    illust_id = url_match.group(2)
                                    page_num = url_match.group(3)
                                    
                                    base_url = f"https://i.pixiv.re/img-original/img/{date_path}/{illust_id}_p{page_num}"
                                    potential_urls = [f"{base_url}.png", f"{base_url}.jpg", f"{base_url}.gif"]
                                    image_url_groups.append(potential_urls)
                                else:
                                    print(f"Could not parse proxy URL: {proxy_url}")
                            
                            if not image_url_groups:
                                await message.channel.send("高画質画像URLの解析に失敗しました。")

                        else:
                            print(f"phixiv API returned status {resp.status} for ID {artwork_id}")
                            await message.channel.send(f"APIエラーが発生しました (Status: {resp.status})。サービスがダウンしている可能性があります。", reference=message)
                            return

            if image_url_groups:
                # ★★★★★ ここからが送信先変更の修正箇所 ★★★★★
                user_id = message.author.id
                # デフォルトは'channel' (DMオフ)
                send_preference = user_settings.get(user_id, 'channel') 
                
                destination = message.author if send_preference == 'dm' else message.channel
                
                await download_and_send_images(destination, image_url_groups, message.channel, message.author)
                # ★★★★★ ここまでが修正箇所 ★★★★★
            else:
                await message.channel.send("このリンクからは画像を見つけられませんでした。")

        try:
            await message.add_reaction('❤️')
        except discord.HTTPException:
            pass

    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        traceback.print_exc()
        await message.channel.send(f"予期せぬエラーが発生しました: `{type(e).__name__}`")

async def process_embed_images(message, embeds):
    image_url_groups = []
    for embed in embeds:
        if embed.image and embed.image.url:
            image_url_groups.append([embed.image.url])

    if not image_url_groups:
        await message.channel.send("この埋め込みには保存できる画像が見つかりませんでした。", reference=message)
        return
    
    user_id = message.author.id
    send_preference = user_settings.get(user_id, 'channel') # デフォルトはチャンネル
    destination = message.author if send_preference == 'dm' else message.channel
    await download_and_send_images(destination, image_url_groups, message.channel, message.author)


def perform_gacha_draw(guaranteed=False):
    weights = GACHA_WEIGHTS_GUARANTEED if guaranteed else GACHA_WEIGHTS_NORMAL
    chosen_category = random.choices(GACHA_ITEMS, weights=weights, k=1)[0]
    return random.choice(chosen_category)

async def send_gacha_results(message):
    results = [perform_gacha_draw() for _ in range(9)]
    results.append(perform_gacha_draw(guaranteed=True))
    await message.channel.send(f"{' '.join(results[0:5])}\n{' '.join(results[5:10])}")

def get_random_shot():
    game = random.choice(SHOT_TYPE)
    return random.choice(game[1:])

# -----------------------------------------------------------------------------
# Discordイベント
# -----------------------------------------------------------------------------
@client.event
async def on_ready():
    print(f'Bot準備完了～ Logged in as {client.user}')
    # ★★★★★ Botのステータスメッセージを更新 ★★★★★
    game = discord.Game("!dmでDM送信ON/OFF")
    await client.change_presence(status=discord.Status.online, activity=game)

@client.event
async def on_message(message):
    if message.author == client.user or message.author.bot:
        return
    
    # ★★★★★ ここからが!dmコマンドの修正箇所 ★★★★★
    if message.content.lower() == '!dm':
        user_id = message.author.id
        current_setting = user_settings.get(user_id, 'channel') # デフォルトは 'channel' (DMオフ)

        if current_setting == 'channel':
            user_settings[user_id] = 'dm'
            await message.channel.send(f"{message.author.mention} 画像のDM送信を **ON** にしました。")
        else:
            user_settings[user_id] = 'channel'
            await message.channel.send(f"{message.author.mention} 画像のDM送信を **OFF** にしました。")
        return
    # ★★★★★ ここまでが修正箇所 ★★★★★

    if message.content.lower() in ["再送信", "download"]:
        if message.reference and message.reference.message_id:
            try:
                referenced_message = await message.channel.fetch_message(message.reference.message_id)
                if referenced_message.embeds:
                    asyncio.create_task(process_embed_images(message, referenced_message.embeds))
                    return
            except discord.NotFound:
                await message.channel.send("返信元のメッセージが見つかりませんでした。", reference=message)
            except discord.Forbidden:
                await message.channel.send("メッセージの読み取り権限がありません。", reference=message)
            return

    if "x.com" in message.content or "twitter.com" in message.content:
        asyncio.create_task(process_media_link(message, 'twitter'))
        return 

    if "pixiv.net" in message.content:
        asyncio.create_task(process_media_link(message, 'pixiv'))
        return

    if GACHA_TRIGGER in message.content:
        await send_gacha_results(message)
        return
        
    if (client.user.mentioned_in(message) or any(keyword in message.content for keyword in ["本日の機体", "今日の機体", "きょうのきたい", "ほんじつのきたい", "イッツルナティックターイム！"])):
        await message.channel.send(get_random_shot())
        return
    if any(keyword in message.content for keyword in ["にゃ～ん", "にゃーん"]):
        await message.channel.send("にゃ～ん")
        return
    if any(keyword in message.content for keyword in ["説明!", "せつめい!"]):
        await message.channel.send("今日の機体、本日の機体 またはメンションで機体出します\n`!dm`で画像のDM送信をON/OFFに切り替えられます。")
        return
    if any(keyword in message.content for keyword in ["ソースコード", "そーす"]):
        await message.channel.send("https://github.com/Kakeyouyou33554432/dis_test")
        return
    if any(keyword in message.content for keyword in ["スタンプ", "すたんぷ"]):
        await message.channel.send(random.choice(STICKER))
        return
    if any(s in message.content for s in STICKER) or "💤" in message.content:
        await message.channel.send(random.choice(STICKER))
        return

@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == client.user.id:
        return

    target_emojis = ['<:sikei:1404428286112825404>', '❤️']
    if str(payload.emoji) not in target_emojis:
        return

    try:
        channel = client.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel):
             return
        message = await channel.fetch_message(payload.message_id)
    except (discord.NotFound, discord.Forbidden):
        return

    if message.author.id != client.user.id:
        return

    if not message.embeds:
        return

    image_url_groups = []
    for embed in message.embeds:
        if embed.image and embed.image.url:
            image_url_groups.append([embed.image.url])

    if not image_url_groups:
        return

    try:
        user = await client.fetch_user(payload.user_id)
    except discord.NotFound:
        return
    
    send_preference = user_settings.get(user.id, 'channel') # デフォルトはチャンネル
    destination = user if send_preference == 'dm' else channel

    success = await download_and_send_images(
        destination=destination,
        image_urls=image_url_groups,
        fallback_channel=channel,
        mention_user=user
    )
    
    if success:
        try:
            found = False
            for reaction in message.reactions:
                if reaction.emoji == payload.emoji and reaction.me:
                    found = True
                    break
            if not found:
                await message.add_reaction(payload.emoji)
        except discord.HTTPException:
            pass

# -----------------------------------------------------------------------------
# 並列起動
# -----------------------------------------------------------------------------
def run_bot():
    bot_token = os.environ.get("DISCORD_BOT_TOKEN")
    if not bot_token:
        print("DISCORD_BOT_TOKENが設定されていません。")
        return

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.create_task(client.start(bot_token))
    
    if not loop.is_running():
        loop.run_forever()


bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
