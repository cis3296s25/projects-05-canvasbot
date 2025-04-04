import nextcord
import os
from dotenv import load_dotenv 
from nextcord.ext import commands, tasks
from nextcord import Interaction
from nextcord.ext.commands import has_permissions, MissingPermissions
import canvasapi
import json
from datetime import datetime as dt
import pytz
from bs4 import BeautifulSoup
from nextcord import Embed
import json

class stud_util(commands.Cog):
    announcement_message = ""
    def __init__(self, client, curr_course = None):
        self.client = client
        self.curr_course = curr_course
        self.user = None
        self.url = None
        self.key = None
        self.pickChoice = None


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
        print(api_key)

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
        API_URL = 'https://templeu.instructure.com/'
        api_key = await self.get_user_canvas(member=interaction.user)
        
        if api_key == 'Please login using the /login command!':
            await interaction.response.send_message(api_key)
            return
        if self.curr_course is None:
            await interaction.response.send_message('Please use `/courses` first and select a course!')
            return
        
        await interaction.response.defer()

        none_upcoming = True
        
        user = canvasapi.Canvas(API_URL, api_key)
 
        assignments = self.curr_course.get_assignments()

        output = f"**Upcoming assingments for {self.curr_course.name}**\n"
        assignment_list = []
        for assignment in assignments:
            assignment_list.append(assignment.__dict__)
            with open('assignments.json', 'w') as file:
                json.dump(assignment_list, file, indent=4, default=str)
            due_date = str(assignment.due_at)

            if due_date == 'None':
                continue
            print(due_date)
            t1 = dt(int(due_date[0:4]), int(due_date[5:7]), int(due_date[8:10]), int(due_date[11:13]), int(due_date[14:16]), tzinfo=pytz.utc)
            t2 = dt.now(pytz.utc)

            if t1 > t2:
                none_upcoming = False

                readable_time = t1.astimezone(pytz.timezone('US/Eastern')).strftime("%H:%M")
                readable_date = t1.strftime("%A, %B %d")

                print(f"{assignment} is due on {readable_date} at {readable_time}\n")
                output += f"```diff\n- {assignment.name} -\ndue on {readable_date} at {readable_time}```\n"
    
        if(none_upcoming):
            await interaction.followup.send(f"You have no upcoming assignments in {user.name}!")
        else: 
            await interaction.followup.send(f"{output}")

    @nextcord.slash_command(name='weekly', description='View the upcoming assignments for the next 7 days.')
    async def view_weekly_assignments(self, interaction : Interaction):
        """
        Views the assignments for all courses due in the next week.
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
        courses = user.get_courses(enrollment_state='active')

        course_dict = {}

        for course in courses:
            try:
                date = int(course.created_at.split('-')[0])
                if date == dt.now().year:
                    print(course.name)
                    course_dict[course] = course.get_assignments(submission_state='unsubmitted')
            except AttributeError:
                print('Error: AttributeError occurred.')

        out : str = ""

        for course, assignments in course_dict.items():
            for assignment in assignments:
                due_date = str(assignment.due_at)
                if due_date == 'None':
                    continue

                due_date = dt.strptime(due_date, '%Y-%m-%dT%H:%M:%SZ')
                time_diff = due_date - dt.utcnow()
                days = time_diff.days

                if days > 7 or days < 0:
                    continue
                elif days == 0:
                    out += f'{assignment.name} is due today.\n'
                elif days == 1:
                    out += f'{assignment.name} is due tomorrow.\n'
                else:
                    out += f'{assignment.name} is due in {days} days.\n'
                        
        await interaction.followup.send(out)

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

        global URL_CANVAS
        global key_api

        URL_CANVAS = 'https://templeu.instructure.com/'
        userCurrent = interaction.user
        key_api = await self.get_user_canvas(member=interaction.user)


        if key_api == 'Please login using the /login command!':
            await interaction.response.send_message(key_api)
            return

        if self.curr_course is None:
            await interaction.followup.send("Please select a course before requesting announcements.", ephemeral=True)
            return
        
        course_str = str(self.curr_course)
        await interaction.followup.send("Do you want to toggle automatic daily announcements for this course? :\n" + course_str)

        output = "+ Enter 1 for yes and 0 for no +\n"
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
                return range(0,2).count(pick) > 0
            
        await self.client.wait_for('message', check=check, timeout = 15)
        pick_str = str(pick)
        print("User's response to automatic announcements: " + pick_str + "\n")
        self.pickChoice = pick
        self.url = URL_CANVAS
        self.key = key_api
        self.user = userCurrent

        if pick == 1:
            print("1")
            self.send_announcements_daily.start()
        elif pick == 0:
            print("0")
        else:
            print("invalid number")




    @tasks.loop(seconds=20)
    async def send_announcements_daily(self):

        if self.pickChoice==1:
            print("Background task running")
            userNew = canvasapi.Canvas(self.url, self.key)
            announcement_pl  = userNew.get_announcements(context_codes=[self.curr_course])
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
            dm_channel = await self.user.create_dm()
            await dm_channel.send(f"Weekly Announcements for {self.curr_course.name} \n\n{message}")
        else:
            print("User is not recieving weekly updates")





def setup(client):
    client.add_cog(stud_util(client))
