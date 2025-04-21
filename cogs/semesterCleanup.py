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
        try:
            await interaction.response.defer(ephemeral=True)
        except nextcord.errors.NotFound:
            print("⚠️ Interaction already expired.")
            return
        
        def is_unsubmitted(assignment, canvas_user_id):
            try:
                submission = assignment.get_submission(canvas_user_id)

                # DEBUG: print submission info
                print(f"\n--- Submission for {assignment.name} ---")
                print(f"ID: {assignment.id}")
                print(f"Due at: {assignment.due_at}")
                print(f"Workflow state: {getattr(submission, 'workflow_state', 'None')}")
                print(f"Submitted at: {getattr(submission, 'submitted_at', 'None')}")
                print(f"Missing: {getattr(submission, 'missing', 'None')}")
                print(f"Score: {getattr(submission, 'score', 'None')}")
                print(f"Submission type: {getattr(submission, 'submission_type', 'None')}")
                print(f"Graded at: {getattr(submission, 'graded_at', 'None')}")
                print("---------------------------")

                if submission is None:
                    return True
                return submission.workflow_state not in ('submitted', 'graded')
            except Exception as e:
                print(f"Couldn't fetch submission for {assignment.name}: {e}")
                return True

            
        def truncate_field(lines, limit=1024):
            result = ""
            for line in lines:
                if len(result) + len(line) + 1 > limit:
                    result += "\n...and more."
                    break
                result += line + "\n"
            return result.strip()


        canvas_token = await self.client.get_cog("stud_util").get_user_canvas(interaction.user)
       
        if not canvas_token or not canvas_token.startswith("9"):
            await interaction.followup.send("Please login using '/login' <token>' first", ephemeral = True)
            return
        
        canvas = Canvas(API_URL, canvas_token)
        canvas_user = canvas.get_current_user()
        canvas_user_id = canvas_user.id

        now = dt.now(pytz.utc)

        overdue = []
        upcoming = []
      

        try:
            courses = {course.id: course for course in canvas.get_courses(enrollment_state='active')}
            for course in courses.values():
                try:
                    for assignment in course.get_assignments():
                        if not assignment.due_at:
                            continue

                        due = dt.strptime(assignment.due_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)

                        # Skip if assignment is older than 90 days
                        if (now - due).days > 90:
                            continue

                        # Skip if already submitted
                        if not is_unsubmitted(assignment, canvas_user_id):
                            continue

                        # Categorize overdue or upcoming
                        if due < now:
                            overdue.append((course.name, assignment, due))
                        elif (due - now).days <= 5:
                            upcoming.append((course.name, assignment, due))

                except Exception as e:
                    print(f"Error fetching assignments for {course.name}: {e}")
        except Exception as e:
            print(f" Error processing {course.name}: {e}")


        embed = Embed(
            title = "Semester Cleanup Report",
            color = nextcord.Color.red()
        )

        if overdue:
            overdue_lines = [
                f"**{c}**: [{a.name}]({a.html_url}) (was due <t:{int(d.timestamp())}:R>)"
                for c, a, d in overdue
            ]
            embed.add_field(
                name="Overdue Assignments",
                value=truncate_field(overdue_lines),
                inline=False
            )
        else:
            embed.add_field(name="No Overdue Assignments!", value = "You're upto date!", inline = False)

        
        if upcoming:
            upcoming_lines = [
                f"**{c}**: [{a.name}]({a.html_url}) (is due <t:{int(d.timestamp())}:R>)"
                for c, a, d in upcoming
            ]
            embed.add_field(
                name="Upcoming Assignments",
                value=truncate_field(upcoming_lines),
                inline=False
            )
        else:
            embed.add_field(name = "No major deadlines in the next 5 days!", value = "How did you do it?? Incredible!", inline=False)
        
        embed.set_footer(text="You’ve got this. One task at a time.")
        await interaction.followup.send(embed=embed, ephemeral=True)
        

def setup(client):
    client.add_cog(SemesterCleanup(client))