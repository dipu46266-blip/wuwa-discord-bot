import os
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
ACTIVEPIECES_WEBHOOK_URL = os.getenv("ACTIVEPIECES_WEBHOOK_URL")

class WuWaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced successfully.")

bot = WuWaBot()
wuwa_group = app_commands.Group(name="wuwa", description="Wuthering Waves tracking commands")

# Tracks channels where automatic updates are active
enabled_channels = set()


async def send_to_activepieces(prompt: str, callback_url: str):
    """Payloads execution prompt and Discord callback URL to Activepieces."""
    if not ACTIVEPIECES_WEBHOOK_URL:
        print("[Error] ACTIVEPIECES_WEBHOOK_URL is missing in environment variables.")
        return

    payload = {
        "prompt": prompt,
        "response_url": callback_url
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(ACTIVEPIECES_WEBHOOK_URL, json=payload) as resp:
                print(f"[Activepieces Dispatch Status]: {resp.status}")
        except Exception as e:
            print(f"[Webhook Send Error]: {e}")


# ==========================================
# ADMIN CONTROLS (AUTO-NOTIFS)
# ==========================================

@wuwa_group.command(name="start", description="[Admin Only] Start automatic news updates in this channel.")
@app_commands.checks.has_permissions(administrator=True)
async def wuwa_start(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in enabled_channels:
        await interaction.response.send_message("⚠️ Automatic updates are already enabled in this channel.", ephemeral=True)
    else:
        enabled_channels.add(channel_id)
        embed = discord.Embed(
            title="✅ Automatic Updates Enabled",
            description=f"This channel will now automatically receive new Wuthering Waves codes, events, and patch details.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)


@wuwa_group.command(name="stop", description="[Admin Only] Stop automatic news updates in this channel.")
@app_commands.checks.has_permissions(administrator=True)
async def wuwa_stop(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in enabled_channels:
        enabled_channels.remove(channel_id)
        embed = discord.Embed(
            title="🛑 Automatic Updates Disabled",
            description="Automatic updates have been disabled for this channel.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("⚠️ Automatic updates are not active in this channel.", ephemeral=True)


# Error Handler for Admin Permission Check
@wuwa_start.error
@wuwa_stop.error
async def admin_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ **Access Denied:** Only Server Administrators can run this command.", ephemeral=True)


# ==========================================
# GENERAL SLASH COMMANDS
# ==========================================

@wuwa_group.command(name="events", description="View active limited-time in-game events and rewards.")
async def wuwa_events(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    strict_prompt = (
        "Search live web for active limited-time events in Wuthering Waves. "
        "Return ONLY a clean JSON object containing active events. Format:\n"
        "{\n"
        '  "events": [\n'
        '    {\n'
        '      "name": "Event Title",\n'
        '      "rewards": "Exact Rewards / Astrite Count",\n'
        '      "how_to_do": "Simple 1-sentence step",\n'
        '      "dates": "Start Date — Expire Date"\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    await send_to_activepieces(strict_prompt, interaction.followup.url)


@wuwa_group.command(name="outside", description="Check for external rewards (Twitch Drops, Discord Check-ins, Web Events).")
async def wuwa_outside(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    strict_prompt = (
        "Search live web for active Wuthering Waves external events outside the game "
        "(e.g., Discord Sign-in, Discord Stream Quests, Twitch Drops, Official Web Events). "
        "Return ONLY a clean JSON object. Format:\n"
        "{\n"
        '  "external_rewards": [\n'
        '    {\n'
        '      "platform": "Discord / Twitch / Web",\n'
        '      "event_name": "Title",\n'
        '      "rewards": "Astrite / Item Count",\n'
        '      "how_to_claim": "Simple step-by-step instruction",\n'
        '      "expiry": "Expiration Date"\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    await send_to_activepieces(strict_prompt, interaction.followup.url)


@wuwa_group.command(name="codes", description="View active redemption codes.")
async def wuwa_codes(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    strict_prompt = (
        "List ONLY currently active or new Wuthering Waves codes. "
        "Do NOT include expired codes, permanent codes, tables, or redemption guides. "
        "Format strictly like this:\n"
        "Active Codes:\n"
        "• `CODE` — Rewards"
    )

    await send_to_activepieces(strict_prompt, interaction.followup.url)


@wuwa_group.command(name="info", description="Get latest version update details and banner phases.")
@app_commands.choices(option=[
    app_commands.Choice(name="recently (Latest Patch Update)", value="recently"),
    app_commands.Choice(name="today (Today's News)", value="today")
])
async def wuwa_info(interaction: discord.Interaction, option: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)

    if option.value == "recently":
        strict_prompt = (
            "Search for latest Wuthering Waves version details and return strictly JSON:\n"
            "{\n"
            '  "patch_version": "Version Number & Title",\n'
            '  "phase_1": {\n'
            '    "new_characters": [{"name": "", "element": "", "weapon": "", "role": "", "image_url": ""}],\n'
            '    "reruns": [{"name": "", "rerun_count": "e.g., 2nd Rerun", "element": "", "role": ""}]\n'
            "  },\n"
            '  "phase_2": {\n'
            '    "new_characters": [{"name": "", "element": "", "weapon": "", "role": "", "image_url": ""}],\n'
            '    "reruns": [{"name": "", "rerun_count": "e.g., 1st Rerun", "element": "", "role": ""}]\n'
            "  }\n"
            "}"
        )
    else:
        strict_prompt = "List ONLY official Wuthering Waves news released today in under 3 bullet points."

    await send_to_activepieces(strict_prompt, interaction.followup.url)


bot.tree.add_command(wuwa_group)


@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} ({bot.user.id})")


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is missing!")
    bot.run(TOKEN)
