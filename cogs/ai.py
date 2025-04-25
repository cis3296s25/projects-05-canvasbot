import nextcord
from nextcord.ext import commands
import json
from openai import AsyncOpenAI

class ai(commands.Cog) :
    def __init__(self, client):
        self.client = client
        self.openai = None

    async def chatgpt(self, message: nextcord.Message,
                       content: str, 
                       imgUrl: str = None) :
        try :
            author = message.author.name
            guildID = str(message.guild.id)

            # Load ai.json to access API key, memory, and chat prompts
            with open("ai.json", "r+") as file:
                data = json.load(file)
                systemPrompt = data.get("systemPrompt")
                guildData = data.get("guilds", {}).get(guildID, {})
                channelId = guildData.get("channelId")
                chatPrompts = guildData.get("chatPrompts", [])

                apiKey = data.get("guilds", {}).get(guildID, {}).get("apiKey")
                if not apiKey:
                    await message.channel.send("No API key found. Please set one using the /ai command.")
                    return
                
                if apiKey:
                    decryptedAPIKey = await self.client.get_cog('RSA').decryptAPIKey(bytes.fromhex(apiKey))
                    self.openai = AsyncOpenAI(api_key=decryptedAPIKey)

                # Update chat prompts with the new message
                if content:
                    chatPrompts.append(f"{author}: {content}")
                if imgUrl:
                    chatPrompts.append(f"{author}: [image]: {imgUrl}")
                chatPrompts = chatPrompts[-7:]  # Keep only the last 7 messages

                # Save the updated chat prompts back to ai.json
                data["guilds"][guildID]["chatPrompts"] = chatPrompts
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
            
            messages = [
                {
                    "role": "system",
                    "content": f"{systemPrompt}"
                },
                {
                    "role": "user",
                    "content": "\n".join(chatPrompts)

                }
            ]
            if imgUrl:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "\n".join(chatPrompts)},
                        {"type": "image_url", "image_url": {"url": imgUrl}},
                    ]
                })
            
            completion = await self.openai.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            responseText = completion.choices[0].message.content

            # Append the AI's response to the chat prompts and save it
            chatPrompts.append(f"AI: {responseText}")
            chatPrompts = chatPrompts[-7:]

            with open("ai.json", "r+") as file:
                data = json.load(file)
                data["guilds"][guildID]["chatPrompts"] = chatPrompts
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
            if len(responseText) <= 2000:
                await message.channel.send(responseText)
            else:
                chunks = [responseText[i:i + 1900] for i in range(0, len(responseText), 1900)]
                for chunk in chunks:
                    await message.channel.send(chunk)

        except Exception as e :
            await message.channel.send(f"An error occurred: {str(e)}")
    
    async def updateJSON(self, guildId, channelId, encryptedKey=None):
        try:
            with open("ai.json", "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {"guilds": {}}

        if str(guildId) not in data["guilds"]:
            data["guilds"][str(guildId)] = {}

        data["guilds"][str(guildId)]["channelId"] = str(channelId)
        data["guilds"][str(guildId)]["chatPrompts"] = []
        if encryptedKey:
            data["guilds"][str(guildId)]["apiKey"] = encryptedKey

        with open("ai.json", "w") as f:
            json.dump(data, f, indent=4)


    @nextcord.slash_command(name="ai", description="Create a new message chat with AI bot")
    async def ai(self, interaction: nextcord.Interaction,
                 api_key: str = nextcord.SlashOption(name="api_key", description="Your OpenAI API key (will override existing key)", required=True)):
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        # Read, encrypt, and write the updated apiKey
        with open("ai.json", "r+") as file:
            data = json.load(file)
            # Encrypt the API key and convert to hex for storage
            encryptedKey = await self.client.get_cog('RSA').encryptAPIKey(api_key)
            encryptedKey = encryptedKey.hex()
            guildID = str(interaction.guild.id)
            if "guilds" not in data:
                data["guilds"] = {}

            if guildID not in data["guilds"]:
                data["guilds"][guildID] = {}

            data["guilds"][guildID]["apiKey"] = encryptedKey
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()


        # Check if guild already has an AI channel
        with open("ai.json", "r") as file:
            data = json.load(file)
            guildID = str(interaction.guild.id)
            if guildID in data.get("guilds", {}) and "channelId" in data["guilds"][guildID]:
                await interaction.response.send_message("This server already has an AI chat channel.", ephemeral=True)
                return

        await interaction.response.send_message("Creating your AI chat channel...", ephemeral=True)

        guild = interaction.guild
        aiChannel = await guild.create_text_channel(name=f"AI")
        await self.updateJSON(interaction.guild.id, aiChannel.id, encryptedKey)

        await interaction.edit_original_message(content="AI chat channel created successfully!")
    

def setup(client):
    client.add_cog(ai(client))