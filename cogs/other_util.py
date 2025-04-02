import nextcord
from nextcord.ext import commands
from nextcord import Interaction
from nextcord.ext.commands import has_permissions, MissingPermissions
from canvasapi import Canvas
from nextcord import SlashOption
import json
''' Cog for other utility commands such as help or logging in. Basically
    things that are not specifically for professor or student. ''' 
class other_util(commands.Cog):
    def __init__(self, client, user_count):
        self.client = client
        self.user_count = user_count

    # Help command.
    @nextcord.slash_command(name='help', description='List command names and descriptions.')
    async def help(self, interaction : Interaction):
        """
        Slash command that lists out the 
        Params:
            interaction : Interaction >> a Discord interaction
            api_key : str >> the user's API key. this is a slash command option
        Returns:
            Nothing
        """
        await interaction.response.send_message(f"Welcome to the Canvas Helper bot!  Here are the commands you can use: \
            \n help - prints this message \
            \n announcements - prints the announcements for the course \
            \n grade - prints your current grade for a course \
            \n poll - creates an embedded poll with vote reactions \
            \n announce - creates an embedded announcement on Dicsord and pins the message \
            \n courses - lists current enrolled courses and allows the user to select one \
            \n login - logs the user into the database using their Canvas access token", ephemeral=True)

    # Login command.
    @nextcord.slash_command(name='login', description='Login to Canvas.')
    async def login(self, interaction : Interaction,
                    api_key : str = SlashOption(name='api_key',
                                                description="Your API Key")):
        """
        Slash command to allow the bot to remember returning users. In order to use the bot, 
        one must login using their API key.
        Params:
            interaction : Interaction >> a Discord interaction
            api_key : str >> the user's API key. this is a slash command option
        Returns:
            Nothing
        """
        
        if await self.is_logged(api_key):
            await interaction.response.send_message('Already logged in!', ephemeral=True)
            return
        
        
        user_snowflake = interaction.user.id
        self.user_count = await self.add_user(api_key=api_key, snowflake=user_snowflake, user_count=self.user_count)

        await interaction.response.send_message("Successfully logged in!", ephemeral=True)

    
    async def is_logged(self, api_key : str, 
                  filename='users.json') -> bool:
        """
        Checks if the user is logged in the database.
        Params: 
            api_key : str >> the user's API key
        Return: 
            bool: true if user is logged, false otherwise
        """
        with open(filename, 'r+') as file:
            file_data = json.load(file)
            for user in file_data['users']:
                if user['apikey'] == api_key:
                    return True
            return False
    
    async def add_user(self, api_key : str,
                       snowflake : int,
                       user_count : int,
                       filename='users.json') -> int:
        """
        Adds a new user to the database.
        Params:
            api_key : str >> the user's API key
            snowflake : nextcord.User.id >> the user's snowflake ID
            user_count : int >> the count of users already in the database
        Returns:
            int : the updated user count
        """
        # Encrypt the API key and convert to hex for storage
        encryptedKey = await self.client.get_cog('RSA').encryptAPIKey(api_key)
        encryptedKey = encryptedKey.hex()
        with open(filename, 'r+') as file:
            file_data = json.load(file)

            # Check if the user already exists
            for user in file_data['users']:
                if user['snowflake'] == snowflake:
                    user['apikey'] = encryptedKey
                    file.seek(0)
                    json.dump(file_data, file, indent=4)
                    file.truncate()
                    return user_count

            # A new user JSON entry
            new_user = {
                'id': user_count,
                'snowflake': snowflake,
                'apikey': encryptedKey
            }
            file_data['users'].append(new_user)
            file.seek(0)
            json.dump(file_data, file, indent=4)
            file.truncate()

        return user_count + 1

        


def setup(client):
    client.add_cog(other_util(client, 0))