import os
import re
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

# Initialize Gemini Client cleanly
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

wuwa_group = app_commands.Group(name="wuwa", description="Wuthering Waves tracking commands")

def extract_image_url(text: str) -> str | None:
    match = re.search(r'https?://\S+\.(?:png|jpg|jpeg|webp|gif)', text, re.IGNORECASE)
    return match.group(0) if match else None


async def fetch_gemini_content(prompt: str) -> tuple[str, str | None]:
    """
    Attempts to fetch content with Google Search grounding.
    Falls back to standard generation if search grounding fails.
    """
    if not ai_client:
        return "❌ `GEMINI_API_KEY` is missing in environment variables.", None

    # Step 1: Attempt Search Grounding with proper types syntax
    try:
        search_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[search_tool])
        
        response = await ai_client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config
        )
        
        source_url = None
        if hasattr(response, 'candidates') and response.candidates:
            grounding = getattr(response.candidates[0], 'grounding_metadata', None)
            if grounding and getattr(grounding, 'grounding_chunks', None):
                for chunk in grounding.grounding_chunks:
                    web_info = getattr(chunk, 'web', None)
                    if web_info and getattr(web_info, 'uri', None):
                        source_url = web_info.uri
                        break

        return response.text or "No information found.", source_url

    except Exception as search_error:
        print(f"Search grounding failed ({search_error}). Falling back to standard generation...")

    # Step 2: Fallback to standard model call without Search Grounding
    try:
        response = await ai_client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text or "No information found.", None
    except Exception as general_error:
        print(f"General Gemini call failed: {general_error}")
        raise general_error


@wuwa_group.command(name="codes", description="View active redemption codes.")
async def wuwa_codes(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    try:
        prompt = (
            "List current active Wuthering Waves redemption codes. "
            "Format cleanly with bullet points:\n"
            "• **Code** — Rewards\n\n"
            "Separate into 'Active Codes' and 'Permanent Codes'."
        )

        ai_text, source_url = await fetch_gemini_content(prompt)

        embed = discord.Embed(
            title="🎁 Wuthering Waves - Active Codes",
            description=ai_text[:3900],
            color=discord.Color.gold()
        )
        if source_url:
            embed.add_field(name="🔗 Source", value=source_url, inline=False)

        embed.set_footer(text="Redeem in-game: Settings -> Other Settings -> Redemption Code")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Error fetching codes: `{e}`")


@wuwa_group.command(name="info", description="Get latest patch details or game news via AI.")
@app_commands.choices(option=[
    app_commands.Choice(name="recently (Latest Patch Update)", value="recently"),
    app_commands.Choice(name="today (Today's News)", value="today")
])
async def wuwa_info(interaction: discord.Interaction, option: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)

    try:
        if option.value == "recently":
            prompt = (
                "Provide details for the latest Wuthering Waves version patch notes. "
                "Structure clearly:\n"
                "**Version**: [Version Number & Title]\n"
                "**New Resonators**: [List new 5-star and 4-star characters]\n"
                "**Patch Highlights**: [3-4 major highlights]\n"
                "**Banner Image**: [Include official banner image URL if available]"
            )
        else:
            prompt = (
                "Provide recent news, maintenance details, or announcements for Wuthering Waves today. "
                "Summarize cleanly."
            )

        ai_text, source_url = await fetch_gemini_content(prompt)
        img_url = extract_image_url(ai_text)

        embed = discord.Embed(
            title=f"📢 Wuthering Waves Update ({option.value.capitalize()})",
            description=ai_text[:3900],
            color=discord.Color.purple()
        )

        if img_url:
            embed.set_image(url=img_url)

        if source_url:
            embed.add_field(name="🌐 Official Source", value=source_url, inline=False)

        embed.set_footer(text="Powered by Gemini AI")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Failed to pull updates: `{e}`")

bot.tree.add_command(wuwa_group)

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} (ID: {bot.user.id})")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is missing!")
    bot.run(TOKEN)
