import os
import json
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = nextcord.Intents.all()
intents.members = True
allowed_mentions = nextcord.AllowedMentions(everyone = True)
client = commands.Bot(command_prefix='c!', intents=intents, allowed_mentions=allowed_mentions)


for file in os.listdir('./cogs'):
    if file.endswith('.py'):
        client.load_extension(f'cogs.{file[:-3]}')
        print(f'Loaded {file}...')

# If users.json doesn't exist, create it with an empty users list
userFile = "users.json"
if not os.path.exists(userFile) or os.path.getsize(userFile) == 0:
    with open(userFile, 'w', encoding='utf-8') as file:
        json.dump({"users": []}, file, indent=4)


# if ai.json doesn't exist, create it with an empty dictionary
aiFile = "ai.json"
if not os.path.exists(aiFile) or os.path.getsize(aiFile) == 0:
    with open(aiFile, 'w', encoding='utf-8') as file:
        json.dump({
            "systemPrompt": "",
            "guildMessages": {}
        }, file, indent=4)


@client.event
async def on_ready():
    print(f"{client.user} is up and running.")


if __name__ == '__main__':
    try:
        client.run(os.getenv('DISCORD'))
    except Exception as e:
        print(f"Main.py: Error occured: {e}")