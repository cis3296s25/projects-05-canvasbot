import nextcord
from nextcord.ext import commands
import json

class ai(commands.Cog) :
    def __init__(self, client):
        self.client = client

    async def updateJSON(self, guildId, channelId):
        try:
            with open("ai.json", "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {
                "systemPrompt": "",
                "guildMessages": {}
            }

        data["guildMessages"][str(guildId)] = str(channelId)

        with open("ai.json", "w") as f:
            json.dump(data, f, indent=4)



    @nextcord.slash_command(name="ai", description="Create a new message chat with AI bot")
    async def ai(self, interaction: nextcord.Interaction,
                 api_key: str = nextcord.SlashOption(name="api_key", description="Your OpenAI API key", required=True)):
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        # Overwrite the API key in the ai.json file
        with open("ai.json", "w") as file:
            data = json.load(file)
            data["apiKey"] = api_key
            file.seek(0)
            json.dump(data, file, indent=4)


        # Check if guild already has an AI channel
        with open("ai.json", "r") as file:
            data = json.load(file)
            guildID = str(interaction.guild.id)
            if guildID in data.get("guildMessages", {}):
                await interaction.response.send_message("This server already has an AI chat channel.", ephemeral=True)
                return

        await interaction.response.send_message("Creating your AI chat channel...", ephemeral=True)

        guild = interaction.guild
        aiChannel = await guild.create_text_channel(name=f"AI")
        await self.updateJSON(interaction.guild.id, aiChannel.id)

        await aiChannel.send(f"{interaction.user.mention}, your AI channel is ready.", emphemeral=True)

def setup(client):
    client.add_cog(ai(client))