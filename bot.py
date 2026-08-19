import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp
import xml.etree.ElementTree as ET

# Fetch secrets securely from Railway environment variables
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

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    
    # Auto-add default channel if configured in Railway
    if DEFAULT_CHANNEL_ID != 0:
        active_channels.add(DEFAULT_CHANNEL_ID)
        print(f"Default channel {DEFAULT_CHANNEL_ID} registered for updates.")
        
    check_wuwa_updates.start()

# --- SLASH COMMANDS ---

@bot.tree.command(name="start", description="Allow Wuthering Waves updates to auto-post in this channel.")
@app_commands.checks.has_permissions(administrator=True)
async def start_updates(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in active_channels:
        await interaction.response.send_message("⚠️ Wuthering Waves updates are already enabled in this channel!", ephemeral=True)
    else:
        active_channels.add(channel_id)
        await interaction.response.send_message("✅ **Wuthering Waves Tracker Activated!** Official news, version updates, and redemption codes will post here.")

@bot.tree.command(name="stop", description="Stop automatic Wuthering Waves updates in this channel.")
@app_commands.checks.has_permissions(administrator=True)
async def stop_updates(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in active_channels:
        active_channels.remove(channel_id)
        await interaction.response.send_message("🛑 **Wuthering Waves Tracker Deactivated.** Auto-posts stopped for this channel.")
    else:
        await interaction.response.send_message("⚠️ Updates are not active in this channel.", ephemeral=True)

@bot.tree.command(name="codes", description="Show active Livestream and Permanent Wuthering Waves redemption codes.")
async def show_codes(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎁 Wuthering Waves - Active Redemption Codes",
        description="Redeem in-game under: **Settings -> Other Settings -> Redemption Code**",
        color=discord.Color.gold()
    )
    embed.add_field(name="📍 Permanent Codes", value="`WUTHERINGGIFT` (50x Astrites)\n`WUWA4PC` (50x Astrites - PC Platform)", inline=False)
    embed.add_field(name="🚨 Livestream / Version Codes", value="Check this channel regularly! New codes drop in BIG letters as soon as announced.", inline=False)
    embed.set_footer(text="Official Kuro Games Code Tracker")
    
    await interaction.response.send_message(embed=embed)

# --- NEWS AUTOMATION ---

@tasks.loop(minutes=10)
async def check_wuwa_updates():
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
                        desc_elem = item.find("description")

                        title = title_elem.text if title_elem is not None else "Wuthering Waves Update"
                        link = link_elem.text if link_elem is not None else ""
                        description = desc_elem.text if desc_elem is not None else ""

                        if link and link not in posted_announcements:
                            posted_announcements.add(link)
                            lower_title = title.lower()

                            # 1. Redemption Codes (BIG Text)
                            if any(k in lower_title for k in ["code", "redemption", "reward", "gift"]):
                                message_text = (
                                    f"# 🚨 NEW REDEMPTION CODE DROPPED 🚨\n"
                                    f"### ➡️ Link: {link}\n"
                                    f"**Announcement:** {title}\n"
                                    f"*Redeem in-game quickly before expiration!*"
                                )
                                await broadcast_message(content=message_text, embed=None)

                            # 2. Version Updates & Banners
                            elif any(k in lower_title for k in ["version", "update", "patch", "preview"]):
                                embed = discord.Embed(
                                    title=f"📢 OFFICIAL UPDATE: {title}",
                                    url=link,
                                    color=discord.Color.purple()
                                )
                                embed.add_field(name="🌐 Official Website URL", value=link, inline=False)
                                embed.add_field(name="⚔️ Banners & Resonators", value="Official character reveals & rerun details in link.", inline=False)
                                embed.add_field(name="⚙️ Bug Fixes & Graphics", value="Includes graphic improvements and game engine fixes.", inline=False)
                                await broadcast_message(content=None, embed=embed)

                            # 3. Maintenance & Compensation
                            elif any(k in lower_title for k in ["maintenance", "compensation", "bug"]):
                                embed = discord.Embed(
                                    title="🔧 MAINTENANCE & COMPENSATION",
                                    description=f"**{title}**\n\nFull details & Astrite compensation:\n{link}",
                                    color=discord.Color.green()
                                )
                                await broadcast_message(content=None, embed=embed)

        except Exception as e:
            print(f"Error checking feeds: {e}")

async def broadcast_message(content=None, embed=None):
    for channel_id in list(active_channels):
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                await channel.send(content=content, embed=embed)
            except Exception as e:
                print(f"Failed to post in channel {channel_id}: {e}")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is missing!")
    bot.run(TOKEN)
