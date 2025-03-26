import nextcord
from nextcord.ext import commands, tasks
import json
import canvasapi
import pytz
from datetime import datetime as dt


API_URL = 'https://templeu.instructure.com/'

class autoAssignmentNotify(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.check_assignments.start()

    '''
    Get the user from the json file and api key
    '''
    def get_user(self, filename='users.json') -> str:
        with open(filename, 'r+') as file:
            fileData = json.load(file)
            return {user['snowflake']: user['api_key'] for user in fileData}
        
    '''
    get assignments from the canvas api that are due in the next 5 days
    '''

    def get_assignments(self, user, api_key):
        user = canvasapi.Canvas(API_URL, api_key)
        courses = user.get_courses(enrollment_state='active')
        assignments = []

        for course in courses:
            try:    
                for assignment in course.get_assignments():
                    if assignment.due_at is not None:
                        due = dt.strptime(assignment.due_at, '%Y-%m-%dT%H:%M:%SZ')
                        now = dt.now(pytz.utc)
                        if (due - now).days <= 5:
                            assignments.append(assignment)
            except Exception as e:
                print(f"Error catching assignments for {course.name}: {e}")

        return assignments


    @tasks.loop(hours=24)
    async def check_assignments(self):
        users = self.get_user()
        for snowflake, api_key in users.items():
            user = canvasapi.Canvas(API_URL, api_key)
            assignments = self.get_assignments(user, api_key)
            if len(assignments) > 0:
                user = self.client.get_user(snowflake)
                for assignment in assignments:
                    await user.send(f"Assignment: {assignment.name} is due in {assignment.due_at}")

    @check_assignments.before_loop
    async def before_check_assignments(self):
        print('waiting...')
        await self.client.wait_until_ready()

