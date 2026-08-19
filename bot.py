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

# Initialize Gemini Client asynchronously if API key exists
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

wuwa_group = app_commands.Group(name="wuwa", description="Wuthering Waves tracking commands")

def extract_image_url(text: str) -> str | None:
    """Helper to extract a direct image URL from text if present."""
    match = re.search(r'https?://\S+\.(?:png|jpg|jpeg|webp|gif)', text, re.IGNORECASE)
    return match.group(0) if match else None


@wuwa_group.command(name="codes", description="View active redemption codes.")
async def wuwa_codes(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    if not ai_client:
        await interaction.followup.send("❌ `GEMINI_API_KEY` is missing in Railway Environment Variables.")
        return

    try:
        prompt = (
            "Perform a Google search for current active Wuthering Waves redemption codes. "
            "Provide a clean list formatted in Markdown:\n"
            "• **Code** — Rewards\n\n"
            "Separate them into 'Active Codes' and 'Permanent Codes'. Keep it concise."
        )

        # Use async Gemini client (.aio) to keep Discord responsive
        response = await ai_client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )

        ai_text = response.text or "No active codes found."

        embed = discord.Embed(
            title="🎁 Wuthering Waves - Active Codes",
            description=ai_text[:3900],
            color=discord.Color.gold()
        )

        # Extract source link if available in grounding metadata
        if hasattr(response, 'candidates') and response.candidates:
            grounding = getattr(response.candidates[0], 'grounding_metadata', None)
            if grounding and getattr(grounding, 'grounding_chunks', None):
                for chunk in grounding.grounding_chunks:
                    web_info = getattr(chunk, 'web', None)
                    if web_info and getattr(web_info, 'uri', None):
                        embed.add_field(name="🔗 Source", value=web_info.uri, inline=False)
                        break

        embed.set_footer(text="Redeem in-game: Settings -> Other Settings -> Redemption Code")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Error fetching codes with AI: {e}")
        await interaction.followup.send("❌ Failed to query AI search for active codes.")


@wuwa_group.command(name="info", description="Get latest patch details or game news via AI.")
@app_commands.choices(option=[
    app_commands.Choice(name="recently (Latest Patch Update)", value="recently"),
    app_commands.Choice(name="today (Today's News)", value="today")
])
async def wuwa_info(interaction: discord.Interaction, option: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)

    if not ai_client:
        await interaction.followup.send("❌ `GEMINI_API_KEY` is missing in Railway Environment Variables.")
        return

    try:
        if option.value == "recently":
            prompt = (
                "Search Google for the latest official Wuthering Waves version update and patch details. "
                "Structure your response with clear sections:\n"
                "**Version**: [Version Number & Title]\n"
                "**New Resonators**: [List new 5-star and 4-star characters/banners]\n"
                "**Patch Highlights**: [3-4 major bullet points about story, events, or regions]\n"
                "**Banner Image**: [Provide a direct URL to a official banner image if available]"
            )
        else:
            prompt = (
                "Search Google for any Wuthering Waves news, maintenance alerts, hotfixes, or announcements posted today. "
                "Summarize key updates cleanly in bullet points."
            )

        # Async request prevents blocking Discord's event loop
        response = await ai_client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )

        ai_text = response.text or "No information found."

        # Extract image if Gemini included an image link
        img_url = extract_image_url(ai_text)

        embed = discord.Embed(
            title=f"📢 Wuthering Waves Update ({option.value.capitalize()})",
            description=ai_text[:3900],
            color=discord.Color.purple()
        )

        if img_url:
            embed.set_image(url=img_url)

        # Append source grounding URL if retrieved
        if hasattr(response, 'candidates') and response.candidates:
            grounding = getattr(response.candidates[0], 'grounding_metadata', None)
            if grounding and getattr(grounding, 'grounding_chunks', None):
                for chunk in grounding.grounding_chunks:
                    web_info = getattr(chunk, 'web', None)
                    if web_info and getattr(web_info, 'uri', None):
                        embed.add_field(name="🌐 Official Source", value=web_info.uri, inline=False)
                        break

        embed.set_footer(text="Powered by Gemini Search Grounding")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Error executing /wuwa info via AI: {e}")
        await interaction.followup.send("❌ Failed to pull updates from AI search.")

bot.tree.add_command(wuwa_group)

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name} (ID: {bot.user.id})")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is missing!")
    bot.run(TOKEN)
