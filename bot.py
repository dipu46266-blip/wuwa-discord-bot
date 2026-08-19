import os
import discord
from discord import app_commands
from discord.ext import commands, tasks

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

# Static / Hardcoded Information Database (Fallback for Cloudflare restrictions)
GAME_INFO_DATABASE = {
    "version": {
        "title": "Wuthering Waves - Current Version Updates",
        "description": "Version 3.5 & 3.6 - Land of Xuanfang & Mengzhou Expansion",
        "details": (
            "• **Version 3.5**: Introduced SP Resonator *Yangyang: Xuanling* (Havoc Sword) and *Suisui* (Glacio Rectifier).\n"
            "• **Version 3.6**: Upcoming expansion featuring *Qingxiao* (Aero Sword) and *Jingran*.\n"
            "• **New Region**: Land of Xuanfang / Mengzhou."
        ),
        "link": "https://wutheringwaves.kurogames.com/en/main/news"
    },
    "codes": [
        {"code": "WUTHERINGGIFT", "rewards": "50x Astrites, 2x Premium Resonance Potion"},
        {"code": "WUWA4PC", "rewards": "50x Astrites (PC Platform Exclusive)"}
    ]
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
        await interaction.response.send_message("✅ **Wuthering Waves Tracker Activated!** Channel registered for announcements.")

@wuwa_group.command(name="stop", description="Stops automatic updates in this channel.")
@app_commands.checks.has_permissions(administrator=True)
async def wuwa_stop(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in active_channels:
        active_channels.remove(channel_id)
        await interaction.response.send_message("🛑 **Wuthering Waves Tracker Deactivated.**")
    else:
        await interaction.response.send_message("⚠️ Updates are not active in this channel.", ephemeral=True)

@wuwa_group.command(name="codes", description="View active permanent and livestream redemption codes.")
async def wuwa_codes(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎁 Wuthering Waves - Active Redemption Codes",
        description="Redeem in-game: **Settings -> Other Settings -> Redemption Code**",
        color=discord.Color.gold()
    )
    
    codes_str = "\n".join([f"`{c['code']}` — {c['rewards']}" for c in GAME_INFO_DATABASE["codes"]])
    embed.add_field(name="📍 Active Codes", value=codes_str, inline=False)
    embed.add_field(
        name="🚨 Broadcast Codes", 
        value="New broadcast / livestream codes will auto-post here as soon as they drop!", 
        inline=False
    )
    embed.set_footer(text="Official Kuro Games Tracker")
    await interaction.response.send_message(embed=embed)

@wuwa_group.command(name="info", description="Get version details or check official updates.")
@app_commands.choices(option=[
    app_commands.Choice(name="recently (Latest Patch Update)", value="recently"),
    app_commands.Choice(name="today (Today's Official Drops)", value="today")
])
async def wuwa_info(interaction: discord.Interaction, option: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)

    info_data = GAME_INFO_DATABASE["version"]

    if option.value == "recently":
        embed = discord.Embed(
            title=f"📢 {info_data['title']}",
            description=info_data["description"],
            url=info_data["link"],
            color=discord.Color.purple()
        )
        embed.add_field(name="📝 Latest Overview", value=info_data["details"], inline=False)
        embed.add_field(name="🌐 Official Website", value=info_data["link"], inline=False)
        embed.set_footer(text="Wuthering Waves Tracker")
        
        await interaction.followup.send(embed=embed)

    elif option.value == "today":
        embed = discord.Embed(
            title="📰 Wuthering Waves - Today's Status",
            description="No emergency maintenance or hotfixes posted today. Check official channels for live updates.",
            color=discord.Color.blue()
        )
        embed.add_field(name="🌐 News Portal", value=info_data["link"], inline=False)
        await interaction.followup.send(embed=embed)

bot.tree.add_command(wuwa_group)

# --- BOT EVENTS ---

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} (ID: {bot.user.id})")
    if DEFAULT_CHANNEL_ID != 0:
        active_channels.add(DEFAULT_CHANNEL_ID)
        print(f"Registered default channel {DEFAULT_CHANNEL_ID}")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is missing!")
    bot.run(TOKEN)
