import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp
from datetime import datetime, timezone

TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "1539528084619792504"))

class WuWaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced successfully.")

bot = WuWaBot()

active_channels = set()
posted_announcements = set()

# Browser headers to prevent Cloudflare / CDN blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://wutheringwaves.kurogames.com/"
}

# Kuro Games Direct Announcement API Endpoint
API_URL = "https://wutheringwaves.kurogames.com/p/api/news/getNewsList?type=0&page=1&pageSize=10"

# --- HELPER FUNCTION TO FETCH DATA SAFELY ---
async def fetch_wuwa_news():
    timeout = aiohttp.ClientTimeout(total=5) # 5-second hard timeout
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        try:
            async with session.get(API_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Verify successful response from Kuro Games API
                    if data.get("code") == 0 or "data" in data:
                        return data.get("data", {}).get("list", [])
        except Exception as e:
            print(f"[API Error] Failed to reach Kuro Games API: {e}")
    return None


# --- COMMAND GROUP SETUP (/wuwa <subcommand>) ---
wuwa_group = app_commands.Group(name="wuwa", description="Wuthering Waves tracking commands")

@wuwa_group.command(name="start", description="Registers this channel to receive automatic updates.")
@app_commands.checks.has_permissions(administrator=True)
async def wuwa_start(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in active_channels:
        await interaction.response.send_message("⚠️ Updates are already enabled in this channel!", ephemeral=True)
    else:
        active_channels.add(channel_id)
        await interaction.response.send_message("✅ **Wuthering Waves Auto-Tracker Activated!** Official news, version updates, and code drops will post here.")

@wuwa_group.command(name="stop", description="Stops automatic updates in this channel.")
@app_commands.checks.has_permissions(administrator=True)
async def wuwa_stop(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in active_channels:
        active_channels.remove(channel_id)
        await interaction.response.send_message("🛑 **Wuthering Waves Auto-Tracker Deactivated.**")
    else:
        await interaction.response.send_message("⚠️ Updates are not active in this channel.", ephemeral=True)

@wuwa_group.command(name="codes", description="View active permanent and livestream redemption codes.")
async def wuwa_codes(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎁 Wuthering Waves - Active Redemption Codes",
        description="Redeem in-game: **Settings -> Other Settings -> Redemption Code**",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="📍 Permanent Codes", 
        value="`WUTHERINGGIFT` — 50x Astrites\n`WUWA4PC` — 50x Astrites (PC Platform)", 
        inline=False
    )
    embed.add_field(
        name="🚨 Broadcast Codes", 
        value="New livestream codes auto-post directly to registered channels in **BIG text** as soon as they drop!", 
        inline=False
    )
    embed.set_footer(text="Official Kuro Games Code Tracker")
    await interaction.response.send_message(embed=embed)

@wuwa_group.command(name="info", description="Get version details or check today's news.")
@app_commands.choices(option=[
    app_commands.Choice(name="recently (Latest Patch Update)", value="recently"),
    app_commands.Choice(name="today (Today's Official Drops)", value="today")
])
async def wuwa_info(interaction: discord.Interaction, option: app_commands.Choice[str]):
    # Defer response immediately to prevent "Interaction Failed"
    await interaction.response.defer()

    news_items = await fetch_wuwa_news()

    if not news_items:
        await interaction.followup.send("❌ Unable to fetch updates from Kuro Games servers right now. Please try again in a moment.")
        return

    try:
        if option.value == "recently":
            latest_update = None
            for item in news_items:
                title = item.get("title", "").lower()
                if any(k in title for k in ["version", "update", "patch", "preview", "notes"]):
                    latest_update = item
                    break
            
            if latest_update:
                title = latest_update.get("title", "Official Announcement")
                news_id = latest_update.get("articleId", "")
                link = f"https://wutheringwaves.kurogames.com/en/main/news/detail/{news_id}" if news_id else "https://wutheringwaves.kurogames.com/"
                snippet = latest_update.get("summary", "") or "Check the official news post for full details."

                embed = discord.Embed(
                    title=f"📢 {title}",
                    url=link,
                    color=discord.Color.purple()
                )
                embed.add_field(name="🌐 Official Announcement Link", value=link, inline=False)
                embed.add_field(name="📝 Details Snippet", value=snippet[:300] + ("..." if len(snippet) > 300 else ""), inline=False)
                embed.set_footer(text="Kuro Games Direct API Tracker")
                
                await interaction.followup.send(embed=embed)
            else:
                # If no specific "patch" tag found, output the most recent general announcement
                top_item = news_items[0]
                title = top_item.get("title", "Latest News")
                news_id = top_item.get("articleId", "")
                link = f"https://wutheringwaves.kurogames.com/en/main/news/detail/{news_id}"
                
                embed = discord.Embed(
                    title=f"📢 Latest Update: {title}",
                    url=link,
                    color=discord.Color.purple()
                )
                embed.add_field(name="🌐 Link", value=link, inline=False)
                await interaction.followup.send(embed=embed)

        elif option.value == "today":
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            found_today = False

            for item in news_items:
                create_time = item.get("createTime", "") # Format: YYYY-MM-DD HH:MM:SS
                if today_str in create_time:
                    found_today = True
                    title = item.get("title", "Official Update")
                    news_id = item.get("articleId", "")
                    link = f"https://wutheringwaves.kurogames.com/en/main/news/detail/{news_id}"

                    embed = discord.Embed(
                        title=f"📰 Today's Official Announcement: {title}",
                        url=link,
                        color=discord.Color.blue()
                    )
                    await interaction.followup.send(embed=embed)
                    break

            if not found_today:
                await interaction.followup.send("ℹ️ No official updates or announcements posted today yet.")

    except Exception as e:
        print(f"Error executing /wuwa info: {e}")
        await interaction.followup.send("❌ An unexpected error occurred while processing the news data.")

# Register command group to bot tree
bot.tree.add_command(wuwa_group)

# --- AUTOMATIC BACKGROUND MONITOR ---

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} (ID: {bot.user.id})")
    if DEFAULT_CHANNEL_ID != 0:
        active_channels.add(DEFAULT_CHANNEL_ID)
        print(f"Registered default channel {DEFAULT_CHANNEL_ID}")
    
    if not check_wuwa_news.is_running():
        check_wuwa_news.start()

@tasks.loop(minutes=10)
async def check_wuwa_news():
    if not active_channels:
        return

    news_items = await fetch_wuwa_news()
    if not news_items:
        return

    for item in reversed(news_items):
        news_id = str(item.get("articleId", ""))
        title = item.get("title", "Wuthering Waves Announcement")
        link = f"https://wutheringwaves.kurogames.com/en/main/news/detail/{news_id}" if news_id else ""

        if news_id and news_id not in posted_announcements:
            posted_announcements.add(news_id)
            lower_title = title.lower()

            # 1. Redemption Codes
            if any(k in lower_title for k in ["code", "redemption", "reward", "gift"]):
                msg = (
                    f"# 🚨 NEW REDEMPTION CODE DROPPED 🚨\n"
                    f"### ➡️ Link: {link}\n"
                    f"**Details:** {title}\n"
                    f"*Redeem in-game immediately before expiration!*"
                )
                await broadcast_message(content=msg)

            # 2. Version Updates
            elif any(k in lower_title for k in ["version", "update", "patch", "preview"]):
                embed = discord.Embed(
                    title=f"📢 OFFICIAL UPDATE: {title}",
                    url=link,
                    color=discord.Color.purple()
                )
                embed.add_field(name="🌐 Official Link", value=link, inline=False)
                await broadcast_message(embed=embed)

            # 3. Maintenance & Compensation
            elif any(k in lower_title for k in ["maintenance", "compensation", "bug"]):
                embed = discord.Embed(
                    title="🔧 MAINTENANCE & COMPENSATIONS",
                    description=f"**{title}**\n\nOfficial Link: {link}",
                    color=discord.Color.green()
                )
                await broadcast_message(embed=embed)

async def broadcast_message(content=None, embed=None):
    for channel_id in list(active_channels):
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                await channel.send(content=content, embed=embed)
            except Exception as e:
                print(f"Error broadcasting to channel {channel_id}: {e}")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is missing!")
    bot.run(TOKEN)
