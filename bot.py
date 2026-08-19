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

# Initialize Gemini Client
ai_client = None
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)

wuwa_group = app_commands.Group(name="wuwa", description="Wuthering Waves tracking commands")

@wuwa_group.command(name="codes", description="View active redemption codes.")
async def wuwa_codes(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    if not ai_client:
        await interaction.followup.send("❌ `GEMINI_API_KEY` is missing in Railway Environment Variables.")
        return

    try:
        prompt = (
            "List all currently active Wuthering Waves redemption codes (including permanent codes and recent livestream codes). "
            "For each code, state what rewards it gives. Keep the response concise, clear, and easy to read."
        )
        
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )

        embed = discord.Embed(
            title="🎁 Wuthering Waves - Active Codes (AI Search)",
            description=response.text[:3900],
            color=discord.Color.gold()
        )
        embed.set_footer(text="Powered by Gemini AI Search")
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
    # Defer immediately to prevent Discord's 3-second timeout
    await interaction.response.defer(thinking=True)

    if not ai_client:
        await interaction.followup.send("❌ `GEMINI_API_KEY` is missing in Railway Environment Variables.")
        return

    try:
        if option.value == "recently":
            prompt = (
                "Search for the latest Wuthering Waves version patch notes and updates. "
                "Provide a clean summary including:\n"
                "1. Current Version Number and Title\n"
                "2. New Characters / Resonators\n"
                "3. Key Features, Events & Story Updates\n"
                "4. A direct image link or banner image URL if available."
            )
        else:
            prompt = (
                "Search for any news, announcements, maintenance alerts, or hotfixes posted for Wuthering Waves today. "
                "Summarize key details briefly."
            )

        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )

        ai_text = response.text or "No information found."

        embed = discord.Embed(
            title=f"📢 Wuthering Waves Info ({option.value.capitalize()})",
            description=ai_text[:3900],
            color=discord.Color.purple()
        )
        
        # Check if Google Search metadata returned an image or source link
        if hasattr(response, 'candidates') and response.candidates:
            grounding = getattr(response.candidates[0], 'grounding_metadata', None)
            if grounding and getattr(grounding, 'grounding_chunks', None):
                for chunk in grounding.grounding_chunks:
                    web_info = getattr(chunk, 'web', None)
                    if web_info and getattr(web_info, 'uri', None):
                        embed.add_field(name="🔗 Source", value=web_info.uri, inline=False)
                        break

        embed.set_footer(text="Fetched dynamically via Gemini Search")
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
