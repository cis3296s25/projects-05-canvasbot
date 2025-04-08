import nextcord
from nextcord.ext import commands
from nextcord import Interaction, Embed
from canvasapi import Canvas
from datetime import datetime as dt, timedelta
import pytz
import json
import os

API_URL = 'https://templeu.instructure.com/'

class SemesterCleanup(commands.Cog):
    def __init__(self, client):
        self.client = client

    @nextcord.slash_command(name = "semester_cleanup", description = "Scan for overdue and upcoming assignments and help get back on track.")
    async def semester_cleanup(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

        canvas_token = await self.client.get_cog("stud_util").get_user_canvas(interaction.user)

        if not canvas_token or not canvas_token.startswith("9"):
            await interaction.followup.send("Please login using '/login' <token>' first", ephemeral = True)
            return
        
        canvas = Canvas(API_URL, canvas_token)
        courses = canvas.get_courses(enrollment_state = 'active')
        now = dt.now(pytz.utc)

        overdue = []
        upcoming = []

        for course in courses:
            try:
                for assignment in course.get_assignment():
                    if not assignment.due_at:
                        continue
                    due = dt.strptime(assignment.due_at, "%Y-%m-%dT%H:%M%S").replace(tzinfo=pytz.utc)

                    if due < now:
                        overdue.append((course.name, assignment, due))
                    elif(due-now).days <= 5:
                        upcoming.append((course.name, assignment, due))
            except Exception as e:
                print(f" Error processing {course.name}: {e}")

        embed = Embed(
            title = "Semester Cleanup Report",
            color = nextcord.Color.red()
        )

        if overdue:
            embed.add_field(
                name = "Overdue Assignments",
                value = "\n".join(
                    #Bold course, clickable markdown link to assignment, discord timestamp, Relative time format
                    f"**{c}**: [{a.name}]({a.html_url}) (was due <t:{int(d.timestamp())}:R>)"
                    for c, a, d in overdue[:5]
                ) + ("\n...and more." if len(overdue) > 5 else ""),
                inline=False
            )
        else:
            embed.add_field(name="No Overdue Assignments!", value = "You're upto date!", inline = False)

        
        if upcoming:
            embed.add_field(
                name = "Up-Coming Assignments",
                value = "\n".join(
                    f"**{c}**: [{a.name}]({a.html_url}) (was due <t:{int(d.timestamp())}:R>)"
                    for c, a, d in overdue[:5]
                ) + ("\n...and more." if len(overdue) > 5 else ""),
                inline=False
            )
        else:
            embed.add_field(name = "No major deadlines in the next 5 days!", value = "How did you do it?? Incredible!", inline=False)
        
        embed.set_footer(text="You’ve got this. One task at a time.")
        await interaction.followup.send(embed=embed, ephemeral=True)

def setup(client):
    client.add_cog(SemesterCleanup(client))