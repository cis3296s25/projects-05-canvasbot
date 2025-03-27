import nextcord
from nextcord.ext import commands, tasks
import json
import canvasapi
import pytz
import binascii
from datetime import datetime as dt

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
            courses = canvas.get_courses(enrollment_state='active')
            for course in courses:
                try:
                    for assignment in course.get_assignments():
                        if assignment.due_at:
                            due = dt.strptime(assignment.due_at, '%Y-%m-%dT%H:%M:%SZ')
                            due = due.replace(tzinfo=pytz.utc)
                            now = dt.now(pytz.utc) 

                            if 0 <= (due - now).days <= 5:
                                assignments.append(assignment)
                except Exception as e:
                    print(f"Error fetching assignments for {course.name}: {e}")
        except Exception as e:
            print(f"Error fetching courses: {e}")

        return assignments



    @tasks.loop(seconds=10)
    async def check_assignments(self):
        users = await self.get_users()  
        print(f"Loaded Users: {users}")

        for snowflake, api_key in users.items():
            print(f"Checking assignments for user: {snowflake}") 
            assignments = self.get_assignments(api_key)
            print(f"Assignments found: {assignments}")

            if assignments:
                user = await self.client.fetch_user(snowflake)
                print(f"Fetched User: {user}") 

                if user:
                    for assignment in assignments:
                        due_date = dt.strptime(assignment.due_at, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S UTC')
                        try:
                            await user.send(f"**Upcoming Assignment:** {assignment.name}\n **Due:** {due_date}")
                            print(f"Sent DM to {user.name}")
                        except Exception as e:
                            print(f"Failed to send DM: {e}")


    @check_assignments.before_loop
    async def before_check_assignments(self):
        print('waiting...')
        await self.client.wait_until_ready()

    @check_assignments.error
    async def check_assignments_error(self, error):
        print(f"Task encountered an error: {error}")


def setup(client):
    client.add_cog(autoAssignmentNotify(client))
