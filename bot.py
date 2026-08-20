import os
import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types

# Load Environment Variables from Railway
TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class WuWaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced successfully.")

bot = WuWaBot()

# Initialize Gemini Client cleanly
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

wuwa_group = app_commands.Group(name="wuwa", description="Wuthering Waves tracking commands")


async def ask_gemini(prompt: str) -> str:
    """Helper function to fetch structured text safely using Gemini 2.5 Flash."""
    if not ai_client:
        return "❌ `GEMINI_API_KEY` is missing in Railway Environment Variables."

    try:
        # Standard fast generation call
        response = await ai_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text or "No data returned."
    except Exception as e:
        print(f"[Gemini Error]: {e}")
        return f"❌ AI Service Error: `{e}`"


@wuwa_group.command(name="codes", description="View active redemption codes.")
async def wuwa_codes(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    prompt = (
        "List all currently active Wuthering Waves redemption codes. "
        "Format cleanly in Markdown:\n"
        "• **Code** — Rewards\n\n"
        "Categorize into 'Active Codes' and 'Permanent Codes'."
    )

    ai_response = await ask_gemini(prompt)

    embed = discord.Embed(
        title="🎁 Wuthering Waves - Active Codes",
        description=ai_response[:3900],
        color=discord.Color.gold()
    )
    embed.set_footer(text="Redeem in-game: Settings -> Other Settings -> Redemption Code")
    await interaction.followup.send(embed=embed)


@wuwa_group.command(name="info", description="Get latest patch details or game news.")
@app_commands.choices(option=[
    app_commands.Choice(name="recently (Latest Patch Update)", value="recently"),
    app_commands.Choice(name="today (Today's News)", value="today")
])
async def wuwa_info(interaction: discord.Interaction, option: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)

    if option.value == "recently":
        prompt = (
            "Summarize the latest version update and patch details for Wuthering Waves. "
            "Structure cleanly using bold section titles:\n"
            "**Version Details**: [Version Number & Title]\n"
            "**New Resonators**: [List featured characters]\n"
            "**Key Highlights**: [Major events, story drops, or new areas]"
        )
    else:
        prompt = (
            "Summarize any official news, maintenance announcements, or event drops "
            "for Wuthering Waves today."
        )

    ai_response = await ask_gemini(prompt)

    embed = discord.Embed(
        title=f"📢 Wuthering Waves Overview ({option.value.capitalize()})",
        description=ai_response[:3900],
        color=discord.Color.purple()
    )
    embed.set_footer(text="Powered by Gemini AI")
    await interaction.followup.send(embed=embed)


bot.tree.add_command(wuwa_group)


@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} (ID: {bot.user.id})")


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is missing!")
    bot.run(TOKEN)
