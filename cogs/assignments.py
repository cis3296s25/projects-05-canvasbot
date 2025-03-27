import nextcord
from nextcord.ext import commands, tasks
import json
import canvasapi
import pytz
from datetime import datetime as dt

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
    async def get_users(self) -> dict:
        users = {}
        stud_util_cog = self.client.get_cog("stud_util") 

        if not stud_util_cog:
            print("stud_util cog not found!")
            return users

        with open('users.json', 'r', encoding='utf-8') as file:
            fileData = json.load(file)
            for user in fileData["users"]:
                snowflake = user['snowflake']
                member = self.client.get_user(snowflake)  
                if member:
                    decrypted_api_key = await stud_util_cog.get_user_canvas(member) 
                    users[snowflake] = decrypted_api_key

        return users
        
    '''
    Get assignments from the Canvas API that are due in the next 5 days
    '''
    def get_assignments(self, api_key):
        canvas = canvasapi.Canvas(API_URL, api_key)
        assignments = []

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
                                assignments.append(assignment)
                except Exception as e:
                    print(f"Error fetching assignments for {course.name}: {e}")
        except Exception as e:
            print(f"Error fetching courses: {e}")

        return assignments


    '''
    Check for assignments every x seconds (for development) 
    check for assignments every 24 hours (for production)

    This function will retrieve the users credentials from users.json
    and then check for assignments for each user. If there are any assignments
    due in the next x days, the user will be messaged with the assignments.
    '''
    @tasks.loop(hours=24)
    async def check_assignments(self):
        users = await self.get_users()  
        print(f"Loaded Users: {users}")

        for snowflake, api_key in users.items(): 
            assignments = self.get_assignments(api_key)

            if assignments:
                user = await self.client.fetch_user(snowflake)
                if user:
                    await self.message(user, assignments, api_key)
    

    '''
    This function will contruct the message (pre-formatted) to be sent to the user
    with the assignments that are due in the next 5 days.
    
    Canvas API does not proivde the course name for each assignment, so we have to
    manually add it to the assignment with course id.
    '''
    async def message(self, user, assignments, api_key):        
        courseAssignments = {}

        canvas = canvasapi.Canvas(API_URL, api_key)
        users_courses = {course.id: course for course in canvas.get_courses(enrollment_state='active')}

        for assignment in assignments:
            course_id = assignment.course_id
            course_name = users_courses.get(course_id, {}).name if course_id in users_courses else "Unknown Course"

            if course_name not in courseAssignments:
                courseAssignments[course_name] = []

            courseAssignments[course_name].append(assignment)

        message = self.format_message(courseAssignments)
        
        try:
            await user.send(message)
        except Exception as e:
            print(f"Failed to send DM: {e}")


    '''
    Format the message to be sent to the user with the assignments that are due in the next 5 days.
    '''
    def format_message(self, courseAssignments):
        message = "**Upcoming Assignments for the Next 5 Days!**\n\n"
        for course, assignments in courseAssignments.items():
            message += f"**{course}**\n"
            for assignment in assignments:
                due = dt.strptime(assignment.due_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
                due_local = due.astimezone(pytz.timezone('US/Eastern'))
                due_str = due_local.strftime('%m/%d/%Y at %I:%M %p') 
                message += f"[{assignment.name}]({assignment.html_url}) - **Due:** {due_str}\n"
            message += "\n"


        return message

    @check_assignments.before_loop
    async def before_check_assignments(self):
        print('waiting...')
        await self.client.wait_until_ready()

    @check_assignments.error
    async def check_assignments_error(self, error):
        print(f"Task encountered an error: {error}")


def setup(client):
    client.add_cog(autoAssignmentNotify(client))
