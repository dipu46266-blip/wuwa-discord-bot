import os
import datetime
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

enabled_channels = set()

async def send_to_activepieces(prompt: str, callback_url: str):
    if not ACTIVEPIECES_WEBHOOK_URL:
        print("[Error] ACTIVEPIECES_WEBHOOK_URL is missing!")
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
# GENERAL SLASH COMMANDS
# ==========================================

@wuwa_group.command(name="events", description="View active limited-time in-game events and rewards.")
async def wuwa_events(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y")

    strict_prompt = (
        f"Today is {today}. Search live web specifically for CURRENT Wuthering Waves in-game LIMITED-TIME EVENTS.\n"
        "RULES:\n"
        "1. Include ONLY playable in-game events (combat challenges, double drops, login events).\n"
        "2. EXCLUDE all banners, character convening, weapon pulls, or external web events.\n"
        "3. Keep total length strictly under 1500 CHARACTERS.\n"
        "4. Return PLAIN TEXT formatted in Discord markdown directly like this:\n\n"
        "📢 **Wuthering Waves — Active In-Game Events**\n\n"
        "🎯 **[Event Name]**\n"
        "• **Rewards:** [Rewards]\n"
        "• **How:** [Short 1-sentence step]\n"
        "• **Req:** [Union Level / Quest req]\n"
        "• **Dates:** [Start — End Date]\n"
    )

    await send_to_activepieces(strict_prompt, interaction.followup.url)


@wuwa_group.command(name="outside", description="Check for external rewards (Twitch Drops, Discord Check-ins, Web Events).")
async def wuwa_outside(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y")

    strict_prompt = (
        f"Today is {today}. Search live web for active Wuthering Waves external events outside the game "
        "(Discord Sign-in, Discord Quests, Twitch Drops, Web Events).\n"
        "Keep total response under 1500 CHARACTERS. Return PLAIN TEXT formatted strictly like this:\n\n"
        "🌐 **Wuthering Waves — External Rewards**\n\n"
        "• **[Platform] Event Name**\n"
        "  - **Rewards:** [Rewards]\n"
        "  - **How to claim:** [Short step]\n"
        "  - **Expires:** [Date]\n"
    )

    await send_to_activepieces(strict_prompt, interaction.followup.url)


@wuwa_group.command(name="codes", description="View active redemption codes.")
async def wuwa_codes(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y")

    strict_prompt = (
        f"Today is {today}. List ONLY currently active or new Wuthering Waves redemption codes. "
        "Do NOT include expired codes or permanent codes. Keep total under 500 characters.\n"
        "Return PLAIN TEXT formatted like this:\n\n"
        "🎁 **Active Wuthering Waves Codes:**\n"
        "• `CODE` — Rewards\n"
    )

    await send_to_activepieces(strict_prompt, interaction.followup.url)


@wuwa_group.command(name="info", description="Get latest version update details and banner phases.")
@app_commands.choices(option=[
    app_commands.Choice(name="recently (Latest Patch Update)", value="recently"),
    app_commands.Choice(name="today (Today's News)", value="today")
])
async def wuwa_info(interaction: discord.Interaction, option: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y")

    if option.value == "recently":
        strict_prompt = (
            f"Today is {today}. Search for current Wuthering Waves version patch details. "
            "Keep response under 1900 CHARACTERS. Return PLAIN TEXT formatted strictly like this:\n\n"
            "⚔️ **Wuthering Waves Patch Update**\n"
            "**Version:** [Patch Number & Title]\n\n"
            "**Phase 1 Banners:**\n"
            "• [New Character/Rerun] — Element | Weapon\n\n"
            "**Phase 2 Banners:**\n"
            "• [New Character/Rerun] — Element | Weapon\n"
            "**Limited Events(In normal details DOnt talk about it too much only what events name asterite count and requirement to it)**\n"
        )
    else:
        strict_prompt = f"Today is {today}. List ONLY official Wuthering Waves news released today in under 3 concise bullet points as plain text."

    await send_to_activepieces(strict_prompt, interaction.followup.url)


bot.tree.add_command(wuwa_group)

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} ({bot.user.id})")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is missing!")
    bot.run(TOKEN)
