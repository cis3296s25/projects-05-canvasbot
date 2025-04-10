import nextcord
import os
from dotenv import load_dotenv 
from nextcord.ext import commands
from nextcord import Interaction
from nextcord.ext.commands import has_permissions, MissingPermissions
import canvasapi
import json
from datetime import datetime as dt
import pytz
from bs4 import BeautifulSoup
from nextcord import Embed
import json
from datetime import datetime as dt

class stud_util(commands.Cog):
    def __init__(self, client, curr_course = None):
        self.client = client
        self.curr_course = curr_course

    def get_letter_grade(self, score: float) -> str:
        if score >= 93: return "A"
        elif score >= 90: return "A-"
        elif score >= 87: return "B+"
        elif score >= 83: return "B"
        elif score >= 80: return "B-"
        elif score >= 77: return "C+"
        elif score >= 73: return "C"
        elif score >= 70: return "C-"
        elif score >= 67: return "D+"
        elif score >= 63: return "D"
        elif score >= 60: return "D-"
        else: return "F"
        
    async def get_user_canvas(self, member : nextcord.User | nextcord.Member,
                        filename = 'users.json') -> str:
        """
        Retrieves the user's API key.
        Params:
            member : Union[nextcord.User, nextcord.Member] >> the user who asked to retrieve their key 
        Return:
            str >> the user's API key
        """
        with open(filename, 'r+', encoding='utf-8') as file:
            fileData = json.load(file)
            for user in fileData["users"]:
                if user['snowflake'] == member.id:
                    apiKey = user.get('apikey')
                    decryptedApiKey = await self.client.get_cog('RSA').decryptAPIKey(bytes.fromhex(apiKey))
                    user['apikey'] = decryptedApiKey
                    return decryptedApiKey
            return "Please login using the /login command!"

    @nextcord.slash_command(name='courses', description='List enrolled courses.')
    async def get_courses(self, interaction : Interaction):
        """
        Slash command to get a course list.
        Params:
            interaction : Interaction >> a Discord interaction 
        Return:
            Nothing
        """
        API_URL = 'https://templeu.instructure.com/'
        api_key = await self.get_user_canvas(member=interaction.user)

        if api_key == 'Please login using the /login command!':
            await interaction.response.send_message(api_key)
            return
        
        user = canvasapi.Canvas(API_URL, api_key)
        courses = user.get_courses(enrollment_state='active')

        await interaction.response.send_message("Here are your courses:\n")

        select = 0
        output = ""
        for course in courses:
            name = course.name
            id = course.id
            output += f"({select}) {name}\n"
            select += 1

        output += "+ Enter a number to select the corresponding course +\n"
        await interaction.followup.send(f"```diff\n{output}```") 

        def check(message : nextcord.message) -> bool:
            """
            Helper method to check a message.
            Params:
                message : nextcord.message >> the message being checked 
            Return:
                bool : whether the pick is valid
            """
            if message.content.isdigit():
                global pick 
                pick = int(message.content)
                return range(0,select).count(pick) > 0
            
        await self.client.wait_for('message', check=check, timeout = 15)
        print(courses[pick].id)
        
        self.curr_course = user.get_course(courses[pick].id)
        await interaction.followup.send(f'Current course: **{courses[pick].name}**\n')

    @nextcord.slash_command(name='upcoming', description='List the upcoming assignments.')
    async def get_upcoming(self, interaction : Interaction):
        """
        Gets upcoming assignments for a specific course.
        Params:
            interaction : Interaction >> a Discord interaction
        Return:
            Nothing
        """
        await interaction.response.defer()

        API_URL = 'https://templeu.instructure.com/'
        api_key = await self.get_user_canvas(member=interaction.user)
        

        other_cog = self.client.get_cog("autoAssignmentNotify")  # 👈 get the cog by name
        if other_cog is None:
            await interaction.followup.send("Error: assignment notifier is not loaded.")
            return
    
        if api_key == 'Please login using the /login command!':
            await interaction.response.send_message(api_key)
            return
        if self.curr_course is None:
            await interaction.response.send_message('Please use `/courses` first and select a course!')
            return
        
        assignments = other_cog.get_assignments(api_key)

        if not assignments:
            await interaction.followup.send("No upcoming assignments found.")
            return
        
        output = "**Upcoming Assignments (Next 5 Days):**\n"
        sorted_assignments = sorted(assignments, key=lambda x: dt.strptime(x.due_at, '%Y-%m-%dT%H:%M:%SZ'))

        for a in sorted_assignments:
            due = dt.strptime(a.due_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
            due_str = due.strftime('%A, %B %d at %I:%M %p UTC')
            output += f"• **{a.name}** (Course: *{a.course_name}*) — due {due_str}\n"

        await interaction.followup.send(output)


    @nextcord.slash_command(name='announcements', description='View announcements from current class')
    async def display_announcements(self, interaction : Interaction):
        """
        Slash command to display announcements for a specific course.
        Params:
            interaction : Interaction >> a Discord interaction
        Return:
            Nothing
        """
        await interaction.response.defer()

        API_URL = 'https://templeu.instructure.com/'
        api_key = await self.get_user_canvas(member=interaction.user)

        if api_key == 'Please login using the /login command!':
            await interaction.response.send_message(api_key)
            return
        
        user = canvasapi.Canvas(API_URL, api_key)
        announcement_pl  = user.get_announcements(context_codes=[self.curr_course])

        announcements = list(announcement_pl)

        if len(announcements) == 0:
            print("No announcements")
            return
        
        for announcement in announcements:
            raw_html = announcement.message
            soup = BeautifulSoup(raw_html, features="html.parser")

            for script in soup(["script", "style"]):
                script.extract()    # rip it out
            text = soup.get_text()
            title = announcement.title
            if(announcement.posted_at is not None):
                posted_at = dt.strptime(announcement.posted_at, '%Y-%m-%dT%H:%M:%SZ')
                formatted_date = posted_at.strftime('%B %d, %Y at %I:%M %p')
                embed = Embed(title=title,
                        description=text,
                        color=nextcord.Color.from_rgb(182, 61, 35),
                        timestamp=posted_at
                        )
            await interaction.followup.send(embed=embed)
            break
    
    @nextcord.slash_command(name='coursegrade', description='View your current grade for a specific course.')
    async def get_course_grade(self, interaction: Interaction, course_number: int):
        """
        
        Gets the current grade and letter grade for a specified course. 
        Params:
            interaction : Interaction >> a Discord interaction
            course_number : int >> Index of the course selected by the user
        Return:
            Nothing
        """
        await interaction.response.defer()

        API_URL = 'https://templeu.instructure.com/'
        api_key = await self.get_user_canvas(member=interaction.user)

        if api_key == 'Please login using the /login command!':
            await interaction.followup.send(api_key)
            return
        
        user = canvasapi.Canvas(API_URL, api_key)
        courses = list(user.get_courses(enrollment_state='active'))

        if course_number < 0 or course_number >= len(courses):
            await interaction.followup.send("Invalid course number. If unsure, use /courses first.")
            return
        
        course = courses[course_number]

        try:
            enrollment = course.get_enrollments(user_id='self')[0]
            grade = enrollment.grades.get('current_score', None)

            if grade is None:
                await interaction.followup.send(f"No grade available for **{course.name}**.")
                return
            
            grade = round(float(grade), 2)
            letter = self.get_letter_grade(grade)

            await interaction.followup.send(f"**{course.name}**\n{grade}% ({letter})")

        except Exception as e:
            print(f"Error fetching grade: {e}")
            await interaction.followup.send("There was an error retrieving the grade. Please try again later.")


    @nextcord.slash_command(name='automatic_announcements', description='Have announcements the from current class automatically sent to you as a dm')
    async def automatic_announcements(self, interaction: Interaction):
        """
        Slash command to send a week's worth of announcements as a direct message
        Params
            interaction: Interaction >>> The Discord interaction
        Returns
            Nothing
        """
        await interaction.response.defer() 

        API_URL = 'https://templeu.instructure.com/'
        api_key = await self.get_user_canvas(member=interaction.user)

        if api_key == 'Please login using the /login command!':
            await interaction.response.send_message(api_key)
            return

        if self.curr_course is None:
            await interaction.followup.send("Please select a course before requesting announcements.", ephemeral=True)
            return
        
        user = canvasapi.Canvas(API_URL, api_key)
        announcement_pl  = user.get_announcements(context_codes=[self.curr_course])
        weekly_list = []
        today = dt.utcnow()
        
        for announcements in announcement_pl:
            if announcements.posted_at is not None:
                posted_at = dt.strptime(announcements.posted_at, '%Y-%m-%dT%H:%M:%SZ')
                day_amount = (today - posted_at).days
                if day_amount <= 7:
                    raw_html = announcements.message
                    soup = BeautifulSoup(raw_html, features="html.parser")
                    desc = soup.get_text().strip()
                    announcement_date = posted_at.strftime('%B %d, %Y at %I:%M %p')
                    weekly_list.append(f"**{announcements.title}**\nPosted on: {announcement_date}\n{desc}\n")

        message = "\n\n".join(weekly_list)
        await interaction.user.send(f" Weekly Announcements for {self.curr_course.name} \n\n{message}")

def setup(client):
    client.add_cog(stud_util(client))
