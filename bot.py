import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp
import xml.etree.ElementTree as ET
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

# Headers to mimic a browser so RSSHub/Cloudflare doesn't block requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

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
    await interaction.response.defer()
    
    # Updated RSS endpoints fallback
    urls = [
        "https://rsshub.app/wutheringwaves/news",
        "https://rsshub.rssforever.com/wutheringwaves/news"
    ]

    text = None
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for url in urls:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if "<rss" in text or "<xml" in text:
                            break
            except Exception as req_err:
                print(f"Failed to fetch from {url}: {req_err}")

    if not text:
        await interaction.followup.send("❌ Unable to connect to Kuro Games RSS feed right now. Please try again later.")
        return

    try:
        root = ET.fromstring(text)

        if option.value == "recently":
            latest_update = None
            for item in root.findall("./channel/item"):
                title_elem = item.find("title")
                if title_elem is not None and title_elem.text:
                    lower_title = title_elem.text.lower()
                    if any(k in lower_title for k in ["version", "update", "patch", "preview"]):
                        latest_update = item
                        break
            
            if latest_update is not None:
                title = latest_update.find("title").text if latest_update.find("title") is not None else "Patch Notes"
                link = latest_update.find("link").text if latest_update.find("link") is not None else "https://wutheringwaves.kurogames.com/"
                desc_elem = latest_update.find("description")
                desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""

                embed = discord.Embed(
                    title=f"📢 {title}",
                    url=link,
                    color=discord.Color.purple()
                )
                embed.add_field(name="🌐 Official Announcement Link", value=link, inline=False)
                
                snippet = desc[:300] + "..." if len(desc) > 300 else desc
                if snippet:
                    embed.add_field(name="📝 Patch Details Snippet", value=snippet, inline=False)

                embed.set_footer(text="Auto-updated from Kuro Games official feed")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("⚠️ Could not find recent patch notes in the official feed.")

        elif option.value == "today":
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            found_today = False

            for item in root.findall("./channel/item"):
                pub_date = item.find("pubDate")
                title_elem = item.find("title")
                link_elem = item.find("link")

                title = title_elem.text if title_elem is not None else "Official Update"
                link = link_elem.text if link_elem is not None else ""

                if pub_date is not None and pub_date.text and today_str in pub_date.text:
                    found_today = True
                    embed = discord.Embed(
                        title=f"📰 Today's Official Announcement: {title}",
                        url=link if link else None,
                        color=discord.Color.blue()
                    )
                    await interaction.followup.send(embed=embed)
                    break

            if not found_today:
                await interaction.followup.send("ℹ️ No official updates or announcements posted today yet.")

    except ET.ParseError:
        print("XML Parsing Error: Received non-XML content from RSS feed.")
        await interaction.followup.send("❌ Received invalid feed data from news provider.")
    except Exception as e:
        print(f"Error executing /wuwa info: {e}")
        await interaction.followup.send("❌ Error processing feed data.")

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

    urls = [
        "https://rsshub.app/wutheringwaves/news",
        "https://rsshub.rssforever.com/wutheringwaves/news"
    ]

    text = None
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for url in urls:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if "<rss" in text or "<xml" in text:
                            break
            except Exception:
                continue

    if not text:
        return

    try:
        root = ET.fromstring(text)
        for item in reversed(root.findall("./channel/item")):
            title_elem = item.find("title")
            link_elem = item.find("link")

            title = title_elem.text if title_elem is not None else "Wuthering Waves Update"
            link = link_elem.text if link_elem is not None else ""

            if link and link not in posted_announcements:
                posted_announcements.add(link)
                lower_title = title.lower()

                if any(k in lower_title for k in ["code", "redemption", "reward", "gift"]):
                    msg = (
                        f"# 🚨 NEW REDEMPTION CODE DROPPED 🚨\n"
                        f"### ➡️ Link: {link}\n"
                        f"**Details:** {title}\n"
                        f"*Redeem in-game immediately before expiration!*"
                    )
                    await broadcast_message(content=msg)

                elif any(k in lower_title for k in ["version", "update", "patch", "preview"]):
                    embed = discord.Embed(
                        title=f"📢 OFFICIAL UPDATE: {title}",
                        url=link,
                        color=discord.Color.purple()
                    )
                    embed.add_field(name="🌐 Official Link", value=link, inline=False)
                    await broadcast_message(embed=embed)

                elif any(k in lower_title for k in ["maintenance", "compensation", "bug"]):
                    embed = discord.Embed(
                        title="🔧 MAINTENANCE & COMPENSATIONS",
                        description=f"**{title}**\n\nOfficial Link: {link}",
                        color=discord.Color.green()
                    )
                    await broadcast_message(embed=embed)
    except Exception as e:
        print(f"Error polling news feed: {e}")

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
