import os
import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types

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
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

wuwa_group = app_commands.Group(name="wuwa", description="Wuthering Waves tracking commands")


async def ask_gemini_with_search(prompt: str) -> str:
    """Queries Gemini 2.5 Flash with live Google Search grounding enabled."""
    if not ai_client:
        return "❌ `GEMINI_API_KEY` is missing in Railway Environment Variables."

    try:
        # Enables live Google Search browsing
        config = types.GenerateContentConfig(
            tools=[{"type": "google_search"}]
        )

        response = await ai_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )
        return response.text or "No data retrieved from web search."
    except Exception as e:
        print(f"[Gemini Search Error]: {e}")
        return f"❌ Search Error: `{e}`"


@wuwa_group.command(name="codes", description="View active redemption codes.")
async def wuwa_codes(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    prompt = (
        "Search the web for all currently active Wuthering Waves redemption codes today. "
        "Format cleanly in Markdown:\n"
        "• **Code** — Rewards\n\n"
        "Categorize into 'Active Codes' and 'Permanent Codes'. Exclude expired livestream codes."
    )

    ai_response = await ask_gemini_with_search(prompt)

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
            "Search Google for the latest official version patch notes for Wuthering Waves. "
            "Structure cleanly:\n"
            "**Version Details**: [Version Number & Title]\n"
            "**New Resonators**: [List featured banner characters]\n"
            "**Key Highlights**: [Major events, story drops, or new areas]"
        )
    else:
        prompt = (
            "Search Google for official Wuthering Waves news, maintenance announcements, or event drops posted today."
        )

    ai_response = await ask_gemini_with_search(prompt)

    embed = discord.Embed(
        title=f"📢 Wuthering Waves Overview ({option.value.capitalize()})",
        description=ai_response[:3900],
        color=discord.Color.purple()
    )
    embed.set_footer(text="Powered by Gemini Search Grounding")
    await interaction.followup.send(embed=embed)


bot.tree.add_command(wuwa_group)


@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} (ID: {bot.user.id})")


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is missing!")
    bot.run(TOKEN)
