import nextcord
from nextcord.ext import commands
from nextcord import Interaction
from nextcord.ext.commands import has_permissions, MissingPermissions

class discussions(commands.Cog):
    def __init__(self, client):
        self.client = client

    @nextcord.slash_command(name='discuss', description='Post a discussion to Canvas.')
    async def post_dsn(self, interaction : Interaction):
        pass

    @nextcord.slash_command(name='reply', description='Reply to a discussion post.')
    async def reply(self, interaction : Interaction):
        pass

def setup(client):
    client.add_cog(discussions(client))