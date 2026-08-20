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


async def trigger_activepieces(prompt: str, response_url: str):
    """Sends the user prompt and Discord callback URL to Activepieces."""
    if not ACTIVEPIECES_WEBHOOK_URL:
        print("[Error] ACTIVEPIECES_WEBHOOK_URL environment variable is missing.")
        return

    payload = {
        "prompt": prompt,
        "response_url": response_url
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(ACTIVEPIECES_WEBHOOK_URL, json=payload) as resp:
                print(f"[Activepieces Trigger Status]: {resp.status}")
        except Exception as e:
            print(f"[Webhook Error]: {e}")


@wuwa_group.command(name="codes", description="View active redemption codes.")
async def wuwa_codes(interaction: discord.Interaction):
    # Tells Discord the bot is processing (gives up to 15 mins to respond)
    await interaction.response.defer(thinking=True)

    prompt = (
        "Search the web for all currently active Wuthering Waves redemption codes today. "
        "Format cleanly in Markdown with bold headers for Active vs Permanent codes."
    )

    # Hand off execution to Activepieces
    await trigger_activepieces(prompt, interaction.followup.url)


@wuwa_group.command(name="info", description="Get latest patch details or game news.")
@app_commands.choices(option=[
    app_commands.Choice(name="recently (Latest Patch Update)", value="recently"),
    app_commands.Choice(name="today (Today's News)", value="today")
])
async def wuwa_info(interaction: discord.Interaction, option: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)

    if option.value == "recently":
        prompt = "Search Google for the latest official version patch notes for Wuthering Waves and list major highlights."
    else:
        prompt = "Search Google for official Wuthering Waves news or announcements posted today."

    # Hand off execution to Activepieces
    await trigger_activepieces(prompt, interaction.followup.url)


bot.tree.add_command(wuwa_group)


@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} (ID: {bot.user.id})")


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is missing!")
    bot.run(TOKEN)
