import nextcord
from nextcord.ext import commands
import json

class ai(commands.Cog) :
    def __init__(self, client):
        self.client = client

    async def updateJSON(self, channel_name) :
        try:
            with open("ai_channels.json", "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}

        # Update the channel name in the JSON data
        data[channel_name] = True

        with open("ai_channels.json", "w") as f:
            json.dump(data, f, indent=4)

    @nextcord.slash_command(name="ai", description="Create a new message chat with AI bot")
    async def ai(self, interaction: nextcord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await interaction.response.send_message("Creating your AI chat channel...", ephemeral=True)

        guild = interaction.guild
        aiChannel = await guild.create_text_channel(name=f"ai-chat-{interaction.user.name}")
        await self.updateJson(aiChannel.name)

        await aiChannel.send(f"{interaction.user.mention}, your AI channel is ready.")

def setup(client):
    client.add_cog(ai(client))