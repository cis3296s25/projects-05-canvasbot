import nextcord
from nextcord import SlashOption, Embed
from nextcord.ext import commands, tasks
import json
import canvasapi
import pytz
from datetime import datetime as dt
import asyncio


'''
This cog will check for assignments due in the next x days for each user every x hours.
If there are any assignments due in the next x days, the user will be messaged with the assignments via discord DM.

This cog requires the stud_util cog to be loaded as it uses the get_user_canvas function to get the users API key.

This cog requires a users.json file to be present in the same directory as the bot. The users.json file should have the following format:

Example users.json:
{
    "users": [
        {
            "snowflake": "1234567890",
            "canvas": "encrypted_api_key"
        },
    ]
}

The users.json file should contain a list of users with their snowflake id and encrypted canvas api key.

The Canvas API URL is set to Temple University's Canvas API URL. This can be changed to any other Canvas API URL.

note: When in development mode, if you keyboardInterrupt (Ex: cntrl + c) the bot, their will be an error dump for now. 
    This is normal and will be fixed in the future.

'''

API_URL = 'https://templeu.instructure.com/'

class autoAssignmentNotify(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.check_assignments.start()

    '''
    Get users and their API keys from users.json
    '''
    async def get_users(self, type_filter="both") -> dict:
        users = {}
        stud_util_cog = self.client.get_cog("stud_util") 

        if not stud_util_cog:
            print("stud_util cog not found!")
            return users

        with open('users.json', 'r', encoding='utf-8') as file:
            fileData = json.load(file)
            for user in fileData["users"]:
                if type_filter == "upcoming" and not user.get("assignmentReminders", True):
                    continue
                if type_filter == "overdue" and not user.get("overdueAssignmentsReminder", True):
                    continue

                snowflake = user['snowflake']
                member = self.client.get_user(snowflake)  
                if member:
                    decrypted_api_key = await stud_util_cog.get_user_canvas(member) 
                    users[snowflake] = decrypted_api_key

        return users
        
    '''
    Get assignments from the Canvas API that are due in the next 5 days using asyncio.
    '''
    async def get_assignments(self, api_key):
        loop = asyncio.get_event_loop()
        assignments = []


        def fetch_assignments():
            canvas = canvasapi.Canvas(API_URL, api_key)
            localAssignments = []

            try:
                courses = {course.id: course for course in canvas.get_courses(enrollment_state='active')}
                for course in courses.values():
                    try:
                        for assignment in course.get_assignments():
                            if assignment.due_at:
                                due = dt.strptime(assignment.due_at, '%Y-%m-%dT%H:%M:%SZ')
                                due = due.replace(tzinfo=pytz.utc)
                                now = dt.now(pytz.utc) 

                                if 0 <= (due - now).days <= 5:
                                    assignment.course_name = courses[course.id].name
                                    localAssignments.append(assignment)
                    except Exception as e:
                        print(f"Error fetching assignments for {course.name}: {e}")
            except Exception as e:
                print(f"Error fetching courses: {e}")

            return localAssignments

        assignments = await loop.run_in_executor(None, fetch_assignments)
        return assignments


    def overdueAssignments(self, api_key):
        '''
        check for assignments that are overdue from the last 5 days 
        '''
        canvas = canvasapi.Canvas(API_URL, api_key)
        overdueAssignments = []

        try:
            courses = {course.id: course for course in canvas.get_courses(enrollment_state='active')}
            for course in courses.values():
                try:
                    for assignment in course.get_assignments():
                        if assignment.due_at:
                            due = dt.strptime(assignment.due_at, '%Y-%m-%dT%H:%M:%SZ')
                            due = due.replace(tzinfo=pytz.utc)
                            now = dt.now(pytz.utc) 

                            if 0 <= (now - due).days <= 5:
                                submission = assignment.get_submission('self')
                                if not submission or (submission.workflow_state == "unsubmitted" and not getattr(submission, "excused", False)):
                                    assignment.course_name = courses[course.id].name
                                    overdueAssignments.append(assignment)

                except Exception as e:
                    print(f"Error fetching assignments for {course.name}: {e}")
        except Exception as e:
            print(f"Error fetching courses: {e}")

        return overdueAssignments

    @tasks.loop(minutes=30)
    async def check_assignments(self):    
        '''
        Check for assignments every x seconds (for development) 
        check for assignments every 24 hours (for production)

        This function will retrieve the users credentials from users.json
        and then check for assignments for each user. If there are any assignments
        due in the next x days, the user will be messaged with the assignments.
        '''
        upcomingUsers = await self.get_users(type_filter="upcoming")  
        overdueUsers = await self.get_users(type_filter="overdue")

        for snowflake, api_key in overdueUsers.items(): 
                    overdueAssignments = self.overdueAssignments(api_key)
                    if overdueAssignments:
                        user = await self.client.fetch_user(snowflake)
                        if user:
                            await self.sendEmbed(
                                user,
                                "Overdue Assignments from the Past 5 Days",
                                self.organizeCourse(overdueAssignments, api_key),
                                0xED4245
                            )
        
       ----
        for snowflake, api_key in upcomingUsers.items(): 
            upcomingAssignments = self.get_assignments(api_key)
            if upcomingAssignments:
                user = await self.client.fetch_user(snowflake)
                if user:
                    await self.sendEmbed(
                        user,
                        "Upcoming Assignments Due in the Next 7 Days",
                        self.organizeCourse(upcomingAssignments, api_key),
                        0x5865F2
                    )
    

    '''
    Sends a nicely formatted embed to the user with the overdue and upcoming assignments.
    The embed will contain the course name and the assignments for that course.
    '''
    async def sendEmbed(self, user, title, courseAssignments, color):
        embed = Embed(title=title, color=color)

        for course, assignments in courseAssignments.items():
            value = ""
            for assignment in assignments:
                due = dt.strptime(assignment.due_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
                due_local = due.astimezone(pytz.timezone('US/Eastern'))
                due_str = due_local.strftime('%m/%d/%Y at %I:%M %p')
                value += f"[{assignment.name}]({assignment.html_url}) — Due: **{due_str}**\n"

            embed.add_field(name=course, value=value[:1024] if value else "No upcoming tasks.", inline=False)

        try:
            await user.send(embed=embed)
        except Exception as e:
            print(f"Failed to send embed to {user}: {e}")


    '''
    Organize the courses and assignments
    '''
    def organizeCourse(self, assignments, api_key):
        canvas = canvasapi.Canvas(API_URL, api_key)
        courseAssignments = {}
        users_courses = {course.id: course for course in canvas.get_courses(enrollment_state='active')}

        for assignment in assignments:
            course_id = assignment.course_id
            course_name = users_courses.get(course_id, {}).name if course_id in users_courses else "Unknown Course"
            if course_name not in courseAssignments:
                courseAssignments[course_name] = []
            courseAssignments[course_name].append(assignment)

        return courseAssignments
    

    '''
    This command will toggle the assignment reminders for the user.
    Users can opt to toggle on and off DMs for both overdue and upcoming assignments that have not been graded
    '''
    @nextcord.slash_command(name='reminders', description="toggle assignment reminders")
    async def reminders( 
        self,   
        interaction: nextcord.Interaction,
        toggle: bool = SlashOption(description="Turn reminders on or off"),
        type: str = SlashOption(description="Type of reminders", choices=["upcoming", "overdue"])):

        with open("users.json", "r", encoding="utf-8") as file:
            data = json.load(file)

        for user in data["users"]:
            if str(user["snowflake"]) == str(interaction.user.id):
                if type == "upcoming":
                    user["assignmentReminders"] = toggle
                elif type == "overdue":
                    user["overdueAssignmentsReminder"] = toggle
                break

        with open("users.json", "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

        await interaction.response.send_message(f"Assignment reminders have been turned {'on' if toggle else 'off'} for {type} assignments.", ephemeral=True)
         
    @check_assignments.before_loop
    async def before_check_assignments(self):
        print('waiting...')
        await self.client.wait_until_ready()

    @check_assignments.error
    async def check_assignments_error(self, error):
        print(f"Task encountered an error: {error}")


def setup(client):
    client.add_cog(autoAssignmentNotify(client))
