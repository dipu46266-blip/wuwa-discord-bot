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
    url = "https://rsshub.app/wutheringwaves/news"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=12) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    root = ET.fromstring(text)

                    if option.value == "recently":
                        # Dynamically search the official feed for the most recent version/patch release
                        latest_update = None
                        for item in root.findall("./channel/item"):
                            title_elem = item.find("title")
                            if title_elem is not None:
                                lower_title = title_elem.text.lower()
                                if any(k in lower_title for k in ["version", "update", "patch", "preview"]):
                                    latest_update = item
                                    break
                        
                        if latest_update is not None:
                            title = latest_update.find("title").text
                            link = latest_update.find("link").text
                            desc = latest_update.find("description").text if latest_update.find("description") is not None else ""

                            embed = discord.Embed(
                                title=f"📢 {title}",
                                url=link,
                                color=discord.Color.purple()
                            )
                            embed.add_field(name="🌐 Official Announcement Link", value=link, inline=False)
                            
                            # Auto-extract preview snippet from feed description
                            snippet = desc[:300] + "..." if len(desc) > 300 else desc
                            if snippet:
                                embed.add_field(name="📝 Patch Details Snippet", value=snippet, inline=False)

                            embed.set_footer(text="Auto-updated from Kuro Games official feed")
                            await interaction.followup.send(embed=embed)
                        else:
                            await interaction.followup.send("⚠️ Could not find recent patch notes in official feeds.")

                    elif option.value == "today":
                        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                        found_today = False

                        for item in root.findall("./channel/item"):
                            pub_date = item.find("pubDate")
                            title_elem = item.find("title")
                            link_elem = item.find("link")

                            title = title_elem.text if title_elem is not None else ""
                            link = link_elem.text if link_elem is not None else ""

                            if pub_date is not None and today_str in pub_date.text:
                                found_today = True
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
            await interaction.followup.send("❌ Error fetching data from Kuro Games official feeds.")

# Register command group to bot tree
bot.tree.add_command(wuwa_group)

# --- AUTOMATIC BACKGROUND MONITOR ---

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} (ID: {bot.user.id})")
    if DEFAULT_CHANNEL_ID != 0:
        active_channels.add(DEFAULT_CHANNEL_ID)
        print(f"Registered default channel {DEFAULT_CHANNEL_ID}")
    check_wuwa_news.start()

@tasks.loop(minutes=10)
async def check_wuwa_news():
    if not active_channels:
        return

    url = "https://rsshub.app/wutheringwaves/news"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=12) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    root = ET.fromstring(text)

                    for item in reversed(root.findall("./channel/item")):
                        title_elem = item.find("title")
                        link_elem = item.find("link")

                        title = title_elem.text if title_elem is not None else "Wuthering Waves Update"
                        link = link_elem.text if link_elem is not None else ""

                        if link and link not in posted_announcements:
                            posted_announcements.add(link)
                            lower_title = title.lower()

                            # 1. Redemption Codes (Auto BIG Text)
                            if any(k in lower_title for k in ["code", "redemption", "reward", "gift"]):
                                msg = (
                                    f"# 🚨 NEW REDEMPTION CODE DROPPED 🚨\n"
                                    f"### ➡️ Link: {link}\n"
                                    f"**Details:** {title}\n"
                                    f"*Redeem in-game immediately before expiration!*"
                                )
                                await broadcast_message(content=msg)

                            # 2. Version Updates (3.6, 3.7, 3.8 auto-handled)
                            elif any(k in lower_title for k in ["version", "update", "patch", "preview"]):
                                embed = discord.Embed(
                                    title=f"📢 OFFICIAL UPDATE: {title}",
                                    url=link,
                                    color=discord.Color.purple()
                                )
                                embed.add_field(name="🌐 Official Link", value=link, inline=False)
                                await broadcast_message(embed=embed)

                            # 3. Maintenance & Compensation Details
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
