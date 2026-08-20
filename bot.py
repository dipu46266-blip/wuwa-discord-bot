import os
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# Retrieve environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
ACTIVEPIECES_WEBHOOK_URL = os.getenv("ACTIVEPIECES_WEBHOOK_URL")


class WuWaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Syncs slash commands globally across Discord servers
        await self.tree.sync()
        print("Slash commands synced successfully.")


bot = WuWaBot()
wuwa_group = app_commands.Group(name="wuwa", description="Wuthering Waves tracking commands")


async def send_to_activepieces(prompt: str, callback_url: str):
    """
    Sends the strict query prompt and Discord interaction followup URL 
    to Activepieces for processing.
    """
    if not ACTIVEPIECES_WEBHOOK_URL:
        print("[Error] ACTIVEPIECES_WEBHOOK_URL environment variable is missing!")
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


@wuwa_group.command(name="codes", description="Get active redemption codes.")
async def wuwa_codes(interaction: discord.Interaction):
    # Prevents Discord 3-second interaction timeout
    await interaction.response.defer(thinking=True)

    strict_prompt = (
        "List ONLY currently active or new Wuthering Waves codes. "
        "Do NOT include expired codes, permanent codes, tables, or redemption guides. "
        "Format strictly like this:\n"
        "Active Codes:\n"
        "• `CODE` — Rewards"
    )

    await send_to_activepieces(strict_prompt, interaction.followup.url)


@wuwa_group.command(name="info", description="Get latest version update highlights.")
@app_commands.choices(option=[
    app_commands.Choice(name="recently (Latest Patch Update)", value="recently"),
    app_commands.Choice(name="today (Today's News)", value="today")
])
async def wuwa_info(interaction: discord.Interaction, option: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)

    if option.value == "recently":
        strict_prompt = (
            "Provide ONLY the latest version update highlights for Wuthering Waves. "
            "Do NOT include paragraphs, guides, or commentary. "
            "Format strictly like this:\n"
            "**Version Update Highlights:**\n"
            "• **Version:** [Number]\n"
            "• **New Characters:** [Names]\n"
            "• **Key Features:** [Short bullet points]"
        )
    else:
        strict_prompt = (
            "List ONLY official Wuthering Waves news or maintenance updates released today. "
            "Keep it under 3 bullet points with no intro or outro text."
        )

    await send_to_activepieces(strict_prompt, interaction.followup.url)


bot.tree.add_command(wuwa_group)


@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} (ID: {bot.user.id})")


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is missing!")
    bot.run(TOKEN)
