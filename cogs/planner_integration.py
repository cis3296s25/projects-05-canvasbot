#Ask user to connect their discord account
#Generate an auth URL with unique state value
#Send user private message with the link
import nextcord
from nextcord.ext import commands
from nextcord import Interaction
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone
from canvasapi import Canvas
from datetime import datetime as dt, timedelta
import pytz
import json
import os

class planner(commands.Cog):
    def __init__(self, client):
        self.client = client
        
    # Slash Command :/connect_google ====================================================================================================
    # Initiates the google OAuth login process by generating an auth URL for the user    
    @nextcord.slash_command(name='connect_google', description='Connect your Google Calendar.')
    async def connect_google(self, interaction : Interaction):
        """
        Slash command to connect the user's Google account via OAuth.
        Params:
            interaction : Interaction >> the Discord interaction context
        Return:
            Nothing
        """
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)                              #User's discord ID string: use in OAuth in flow state
        auth_url = self.generate_google_auth_url(user_id)               #Gen OAuth URL with user ID embedded in the state


        await interaction.followup.send(
            f"Click here to connect your Google Calendar: {auth_url}", 
            ephemeral=True)                                             # Make the message visible only to the user

            
    # Calendar test =======================================================================================================    
    @nextcord.slash_command(name="calendar_test", description="Show 3 upcoming Google Calendar events.")
    async def calendar_test(self, interaction: Interaction):
        user_id = str(interaction.user.id)

        await interaction.response.defer(ephemeral=True)
        """
        Slash command to fetch and display the user's next 3 calendar events.
        Params:
            interaction : Interaction >> the Discord interaction context
        Return:
            Nothing
        """

        user_id = str(interaction.user.id)


        try:
            with open(f"tokens/{user_id}.json", "r") as f:
                creds = Credentials(**json.load(f))

            
            service = build("calendar", "v3", credentials=creds)
            now = datetime.now(timezone.utc).isoformat()


            # Get the next 3 events
            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=3,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = events_result.get("items", [])

            if not events:
                await interaction.followup.send("No upcoming events found.", ephemeral=True)
                return

            response = "\n".join(
                f"{e['start'].get('dateTime', e['start'].get('date'))} - {e['summary']}"
                for e in events
            )

            await interaction.followup.send(f"Upcoming events:\n{response}", ephemeral=True)

        except FileNotFoundError:
            await interaction.followup.send("You haven’t connected your calendar yet. Use `/connect_google`.", ephemeral=True)
        except Exception as e:
            print("Error reading calendar:", e)
        
            await interaction.followup.send("Error retrieving calendar events.", ephemeral=True)
    
    # Sync Canvas to Calendar ==============================================================================================================
    @nextcord.slash_command(name="sync_canvas_to_calendar", description="Synchronize your Canvas Assignments to Google Calendar.")
    async def sync_canvas_to_calendar(self, interaction: Interaction):
 
    
        """
        Slash command to fetch Canvas assignments and push them to Google Calendar.
        Params:
            interaction : Interaction >> the Discord interaction context
        Return:
            Nothing
        """
        try:
            await interaction.response.defer(ephemeral=True)
        except nextcord.errors.NotFound:
            print("Interaction already expired. skipping defer.")
            return
        
        user_id = str(interaction.user.id)
        assignment_count = 0 
     

        try:
            # Retrieve Canvas Token
            canvas_token = await self.client.get_cog("stud_util").get_user_canvas(interaction.user)
           
            if canvas_token.startswith("Please login") or canvas_token.startswith("1"):
                await interaction.followup.send("Please login using `/login <token>` first.", ephemeral=True)
                return

            
            #Load Google Credentials
            with open(f"tokens/{user_id}.json", "r") as f:
                creds = Credentials(**json.load(f))
            calendar_service = build("calendar", "v3", credentials = creds)

                
            # Load user’s color selections
            color_path = f"course_colors/{user_id}.json"
            if not os.path.exists(color_path):
                await interaction.followup.send(
                    "❗ You need to run `/setup_colors` first to choose which Canvas classes to sync.\n"
                    "Only courses with colors set will be synced to Google Calendar.",
                    ephemeral=True
                )
                return

            with open(color_path, "r") as f:
                course_colors = json.load(f)
          

            await interaction.followup.send(
                "⏳ Syncing only the courses you've picked colors for...",
                ephemeral=True
            )


            # Get Canvas assignments
            canvas = Canvas("https://templeu.instructure.com/", canvas_token)
            #courses = canvas.get_courses(enrollment_state="active")
            courses = [
                c for c in canvas.get_courses(enrollment_state="active")
                if hasattr(c, "workflow_state") and c.workflow_state == "available"
            ]

          

            for course in courses:
                course_id = str(course.id)
                if course_id not in course_colors:
                    continue  # skip if user didn’t choose a color

                for assignment in course.get_assignments():
                    if not assignment.due_at:
                        continue

                    due_time = dt.strptime(assignment.due_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
                    if due_time < dt.now(pytz.utc):
                        continue  # skip past due

                    event = {
                        'summary': f"{course.name}: {assignment.name}",
                        'description': f"Canvas assignment for {course.name}.",
                        'start': {
                            'dateTime': due_time.isoformat(),
                            'timeZone': "America/New_York"
                        },
                        'end': {
                            'dateTime': (due_time + timedelta(minutes=30)).isoformat(),
                            'timeZone': "America/New_York"
                        },
                        'colorId': course_colors[course_id]['color']
                    }
                    # Check if event already exists
                    existing_events = calendar_service.events().list(
                        calendarId="primary",
                        timeMin=due_time.isoformat(),
                        timeMax=(due_time + timedelta(minutes=1)).isoformat(),
                        q=assignment.name,
                        singleEvents=True
                    ).execute().get("items", [])

                    already_exists = any(
                        e["summary"] == event["summary"]
                        for e in existing_events
                    )

                    if already_exists:
                        continue


                    calendar_service.events().insert(calendarId="primary", body=event).execute()
                    assignment_count += 1

                if assignment_count == 0:
                    await interaction.followup.send("📭 No upcoming assignments to sync.", ephemeral=True)
                else:
                    await interaction.followup.send(f"✅ Synced {assignment_count} assignments to your Google Calendar!", ephemeral=True)

        except FileNotFoundError:
            await interaction.followup.send("Google Calendar is not connected. Use `/connect_google` first.", ephemeral=True)
        except Exception as e:
            print("Sync error:", e)
            print(f"Synced {assignment_count} assignments before error.")
            await interaction.followup.send("⚠️ An error occurred while syncing assignments.", ephemeral=True)


    @nextcord.slash_command(name="setup_instructions", description="Get step-by-step instructions for connecting Google Calendar.")
    async def setup_instructions(self, interaction: Interaction):
        embed = nextcord.Embed(
            title="📆 Google Calendar Setup Guide",
            description=(
                "**Step 1:** Run the OAuth server\n"
                "`python web/oauth_server.py`\n\n"
                "**Step 2:** Use `/connect_google`\n"
                "Login and authorize access to your Google account.\n\n"
                "**Step 3:** Use `/setup_colors`\n"
                "Pick which courses to sync (only those with colors will appear on your calendar).\n\n"
                "**Step 4:** Use `/sync_canvas_to_calendar`\n"
                "Adds your Canvas assignments to Google Calendar. You can re-run this anytime.\n\n"
                "🔁 *If anything breaks, delete your token file in `/tokens/` and repeat Step 2.*"
            ),
            color=nextcord.Color.blurple()
        )
        embed.set_footer(text="CanvasBot Setup")
        await interaction.response.send_message(embed=embed, ephemeral=True)


    # Helper function to generate a Google OAuth authorization URL
    # Uses the client secrets file, required scopes, and redirect URI
    # User's Discord ID passed as the "state" to identify them later
    def generate_google_auth_url(self, user_id):
        """
        Helper function to generate the Google OAuth URL.
        Params:
            user_id : str >> the Discord user ID to store in OAuth state
        Return:
            str : the authorization URL
        """
        flow = Flow.from_client_secrets_file(
            "credentials.json",                                         # Your Google API credential's file
            scopes=["https://www.googleapis.com/auth/calendar.events"], #scope to read/write calendar events
            redirect_uri=os.getenv("GOOGLE_REDIRECT_URI")               # Must match Flask app's /oauth2callback route
        )

        # Built the authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',                                      # Request a refresh token for long-term access
            prompt='consent',                                           # Force showing the consent screen to ensure refresh token is returned
            include_granted_scopes='true',                              # Preserve previously granted scopes
            state=user_id                                               # Embed Discord user ID so we can match the token to the user later
        )
        return auth_url                                                 # Return the fully-formed URL




# Register this cog with the bot
def setup(client):
    client.add_cog(planner(client))