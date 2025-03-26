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

    async def get_users(self, filename='users.json') -> dict:
        try:
            with open(filename, 'r') as file:
                fileData = json.load(file)

                users = {}
                for user in fileData["users"]:
                    snowflake = user['snowflake']
                    encrypted_api_key_hex = user['apikey']

                    print(f"Encrypted API Key (HEX): {encrypted_api_key_hex}")

                    try:
                        encrypted_api_key_bytes = binascii.unhexlify(encrypted_api_key_hex)
                        print(f"Decoded API Key (Raw Bytes): {encrypted_api_key_bytes}")
                    except Exception as e:
                        print(f"HEX Decoding Error: {e}")
                        continue 

                    decrypted_api_key = await self.client.get_cog('RSA').decryptAPIKey(encrypted_api_key_bytes)
                    
                    users[snowflake] = decrypted_api_key

                return users

        except (json.JSONDecodeError, FileNotFoundError, KeyError, TypeError) as e:
            print(f"Error reading {filename}: {e}")
            return {}

        
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

                            if (due - now).days <= 5:
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
