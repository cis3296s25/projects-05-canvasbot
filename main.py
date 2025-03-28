import os
import json
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv

load_dotenv(dotenv_path='/Users/andrewrush/Desktop/3296-stuff/projects-05-canvasbot/.env')

intents = nextcord.Intents.all()
intents.members = True
allowed_mentions = nextcord.AllowedMentions(everyone = True)
client = commands.Bot(command_prefix='c!', intents=intents, allowed_mentions=allowed_mentions)

@client.event
async def on_ready():
    print(f"{client.user} is up and running.")

for file in os.listdir('./cogs'):
    if file.endswith('.py'):
        client.load_extension(f'cogs.{file[:-3]}')
        print(f'Loaded {file}...')

# If users.json doesn't exist, create it with an empty users list
userFile = "users.json"
if not os.path.exists(userFile) or os.path.getsize(userFile) == 0:
    with open(userFile, 'w', encoding='utf-8') as file:
        json.dump({"users": []}, file, indent=4)



if __name__ == '__main__':
    try:
        client.run(os.getenv('DISCORD'))
    except Exception as e:
        print(f"Main.py: Error occured: {e}")