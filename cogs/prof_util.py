import nextcord
from nextcord.ext import commands
from nextcord import Interaction
from nextcord.ext.commands import has_permissions, MissingPermissions
from nextcord import SlashOption
from nextcord import Embed
from datetime import datetime

class prof_util(commands.Cog):
    def __init__(self, client):
        self.client = client

    @nextcord.slash_command(name='announce', description='Make an announcement.')
    async def announcement(self, interaction : Interaction, 
                           title : str = SlashOption(name='title'), 
                           content : str = SlashOption(name='content')):
        """
        Slash command to create an embedded announcement and pin it.
        Params:
            interaction : Interaction >> a Discord interaction
            title : str >> the title of the poll
            content : str >> the content of the announcement 
        Return:
            Nothing
        """

        embed = Embed(title=title,
                      description= content,
                      color=interaction.user.color,
                      timestamp=datetime.utcnow()
                      )
        await interaction.response.send_message(embed=embed)
        
        # Pin the announcement for ease of access and to show importance.
        message = self.find_embed(interaction=interaction, embed=embed)
        message.pin


    @nextcord.slash_command(name='poll', description='Create a poll.')
    async def create_poll(self, 
                          interaction : Interaction,
                          question : str = SlashOption(name='question'),
                          options : str = SlashOption(name='options')):
        """
        Slash command to create an embedded poll with reactions.
        Params:
            interaction : Interaction >> a Discord interaction
            question : str >> the Poll question
            options : >> the voting options
        Return:
            Nothing
        """

        numbers = ("1️⃣", "2⃣", "3⃣", "4⃣", "5⃣",
		   "6⃣", "7⃣", "8⃣", "9⃣", "🔟")

        options_list = options.split()
            
        if len(options_list) > 10:
            await interaction.response.send_message("You can only supply a maximum of 10 options.")
            return

        # Create embed object to embed poll title and fields
        embed = Embed(title='Poll',
                      description=question,
                      color=interaction.user.color,
                      timestamp=datetime.utcnow()
                      )
        
        # Fields array. Each tuple contains a header (1st element), text (2nd element), and a boolean variable that determines inline
        fields=[("Options", "\n".join([f'{numbers[i]} {option}' for i, option in enumerate(options_list)]), False),
                ("Instructions", "React to cast a vote.", False)]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await interaction.response.send_message(embed=embed)
        
         # Loop through channel history and pull the message that matches (should be first)
         # This is for reacting to the embed, so that our poll has options users can choose.
        vote = self.find_embed(interaction=interaction, embed=embed)
            
        for emoji in numbers[:len(options_list)]:
            await vote.add_reaction(emoji)
        

    # Method to find the embed that matches a given embed.    
    async def find_embed(interaction : Interaction,
                         embed : Embed) -> nextcord.Message:
        """
        Finds the embed that matches a given embed (this is solely for adding reactions)
        Params:
            interaction : Interaction >> a Discord interaction
            embed : Embed >> the Discord embed we are searching for
        Return:
            nextcord.Message >> the message to add reactions to
        """

        message: nextcord.Message
        async for message in interaction.channel.history():
            if not message.embeds:
                continue
            # title and color of the embed matches our embed.
            if message.embeds[0].title == embed.title and message.embeds[0].color == embed.color:
                return message
            else:
            # something broke
                return None

def setup(client):
    client.add_cog(prof_util(client))