import nextcord
import os
from dotenv import load_dotenv 
from nextcord.ext import commands
from nextcord.ext import tasks
from nextcord import Interaction
from nextcord.ext.commands import has_permissions, MissingPermissions
import canvasapi
import json
from datetime import datetime as dt
import pytz
from bs4 import BeautifulSoup
from nextcord import Embed
import json
from nextcord.ext import tasks
import asyncio
from nextcord import Embed
from datetime import datetime as dt
from nextcord.ui import Select, View, Button
from nextcord import SelectOption

class stud_util(commands.Cog):
    def __init__(self, client, curr_course = None):
        self.client = client
        self.curr_course = curr_course
        self.user = None
        self.url = None
        self.key = None
        self.pickChoice = None

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

    def convert_to_gpa_scale(self, percentage: float) -> float:
        """
        Converts percentage grade to 4.0 GPA scale.
        
        Args:
            percentage: Percentage grade (0-100)
            
        Returns:
            float: GPA points on a 4.0 scale
        """
        if percentage >= 93: return 4.0
        elif percentage >= 90: return 3.7 # A-
        elif percentage >= 87: return 3.3  # B+
        elif percentage >= 83: return 3.0  # B
        elif percentage >= 80: return 2.7  # B-
        elif percentage >= 77: return 2.3  # C+
        elif percentage >= 73: return 2.0  # C
        elif percentage >= 70: return 1.7  # C-
        elif percentage >= 67: return 1.3  # D+
        elif percentage >= 63: return 1.0  # D
        elif percentage >= 60: return 0.7  # D-
        else: return 0.0  # F
            
    class GPACalculateView(nextcord.ui.View):
        def __init__(self, course_data):
            super().__init__(timeout=300)
            self.course_data = course_data
            self.add_item(stud_util.GPACalculateButton(self.course_data))

    class GPACalculateButton(nextcord.ui.Button):
        def __init__(self, course_data):
            super().__init__(label="Calculate GPA", style=nextcord.ButtonStyle.primary)
            self.course_data = course_data

        async def callback(self, interaction: nextcord.Interaction):
            if any(course.get('credits') is None for course in self.course_data):
                await interaction.response.send_message(
                    "Please select credit hours for all courses first.", ephemeral=True
                )
                return

            total_points = sum(course['gpa_points'] * course['credits'] for course in self.course_data)
            total_credits = sum(course['credits'] for course in self.course_data)

            if total_credits == 0:
                await interaction.response.send_message("Total credits is zero. Cannot compute GPA.", ephemeral=True)
                return
            
            semester_gpa = round(total_points / total_credits, 2)

            output = f"**Your current semester GPA is: {semester_gpa}**\n\n"
            output += "Course breakdown:\n"
            for course in self.course_data:
                output += f"- {course['name'][:40]}... ({course['grade']}%) -> {course['gpa_points']} GPA × {course['credits']} credits\n"

            await interaction.response.send_message(output)

    class CombinedCreditHourView(nextcord.ui.View):
        def __init__(self, course_data):
            super().__init__(timeout=300)
            self.course_data = course_data

            # Add a dropdown for each course
            for index in range(len(course_data)):
                self.add_item(stud_util.CreditHourDropdown(course_data, index))

    class CreditHourDropdown(nextcord.ui.Select):
        def __init__(self, course_data, index):
            self.course_data = course_data
            self.index = index

            options = [
                nextcord.SelectOption(label=f"{j} Credits", value=str(j))
                for j in range(1, 6)
            ]

            super().__init__(
                placeholder=f"Select Credits for Course {self.index + 1}",
                options=options,
                min_values=1,
                max_values=1,
                row=self.index
            )

        # Pre-fill default if not already set
            if self.course_data[self.index].get('credits') is None:
                self.course_data[self.index]['credits'] = 3

        async def callback(self, interaction: nextcord.Interaction):
            self.course_data[self.index]['credits'] = int(self.values[0])
            await interaction.response.defer()        

    async def create_credit_hour_selection(self, interaction, course_data):
        for course in course_data:
            if course.get('credits') is None:
                course['credits'] = 3
        
        description = "\n".join([f"Course {i+1}: {course['name'][:80]}" for i, course in enumerate(course_data)])
        embed = nextcord.Embed(
            title="Select Credit Hours",
            description=description,
            color=nextcord.Color.blurple()
        )
        
        await interaction.followup.send(
            embed=embed,
            view=stud_util.CombinedCreditHourView(course_data),
            ephemeral=True
        )

        await interaction.followup.send(
            "Once all credits are set, click below to calculate your GPA. If no selection is made for a course, it will default to 3 credits: ",
            view=stud_util.GPACalculateView(course_data),
            ephemeral=True
        )

    async def get_user_canvas(self, member : nextcord.User | nextcord.Member,
                        filename = 'users.json') -> str:
        """
        Retrieves the user's API key.
        Params:
            member : Union[nextcord.User, nextcord.Member] >> the user who asked to retrieve their key 
        Return:
            str >> the user's API key
        """
        try:
            with open(filename, 'r+', encoding='utf-8') as file:
                fileData = json.load(file)
                for user in fileData["users"]:
                    if user['snowflake'] == member.id:
                        apiKey = user.get('apikey')
                        decryptedApiKey = await self.client.get_cog('RSA').decryptAPIKey(bytes.fromhex(apiKey))
                        user['apikey'] = decryptedApiKey
                        return decryptedApiKey
                return "please login using the /login command"
        except Exception as e:
                    print(f"Error retrieving API key {e}")
                    return "Error retrieving your API key. Please try logging in again."
            
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
            await interaction.response.send_message(api_key, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        user = canvasapi.Canvas(API_URL, api_key)
        all_courses = user.get_courses(enrollment_state='active')
        courses = []
        current_month = dt.now().month
        current_year = dt.now().year
        previous_month = current_month - 1 if current_month > 1 else 12
        previous_month_year = current_year if current_month > 1 else current_year - 1

        for course in all_courses:
            try:
                assignments = list(course.get_assignments())
                has_relevant_assignments = False

                for assignment in assignments:
                    if hasattr(assignment, 'due_at') and assignment.due_at:
                        try:
                            due_date = dt.strptime(assignment.due_at, '%Y-%m-%dT%H:%M:%SZ')
                            if (due_date.year == current_year and due_date.month == current_month) or \
                            (due_date.year == previous_month_year and due_date.month == previous_month):
                                has_relevant_assignments = True
                                break
                        except Exception:
                            continue

                if has_relevant_assignments or "2025" in course.name:
                    courses.append(course)

            except Exception as e:
                print(f"Error processing course {course.name}: {e}")
        
        if not courses:
            await interaction.response.send_message("No current courses found based on recent activity.",ephemeral=True)
            return

        options = [
            SelectOption(label=course.name, value=str(i)) for i, course in enumerate(courses)
        ]

        select = Select(
            placeholder="Select a course",
            options=options,
            min_values=1,
            max_values=1)
        
        async def callback(callBackInteraction: Interaction):
            index = int(select.values[0])
            view.touched = True
            self.curr_course = user.get_course(courses[index].id)
            await callBackInteraction.response.edit_message(content=f"Selected course: **{courses[index].name}**", view=None)

        select.callback = callback
        class CourseSelectView(View):
            def __init__(self, timeout=30):
                super().__init__(timeout=timeout)
                self.message = None
                self.touched = False

            async def on_timeout(self):
                if self.touched:
                    return
                await self.message.edit(content="Select timed out. Please run '/courses' again to select a course.", view=None)

        view = CourseSelectView(timeout=30)
        view.add_item(select)
        await interaction.followup.send("Select a course:", view=view, ephemeral=True)
        view.message = await interaction.original_message()


    @nextcord.slash_command(name='upcoming', description='List the upcoming assignments.')
    async def get_upcoming(self, interaction : Interaction):
        """
        Gets upcoming assignments for a specific course.
        Params:
            interaction : Interaction >> a Discord interaction
        Return:
            Nothing
        """
        await interaction.response.defer(ephemeral=True)

        API_URL = 'https://templeu.instructure.com/'
        api_key = await self.get_user_canvas(member=interaction.user)
        

        other_cog = self.client.get_cog("autoAssignmentNotify")  # 👈 get the cog by name
        if other_cog is None:
            await interaction.followup.send("Error: assignment notifier is not loaded.")
            return
        
        if api_key == 'Please login using the /login command!':
            await interaction.followup.send(api_key)
            return

        assignments = await other_cog.get_assignments(api_key)

        if not assignments:
            await interaction.followup.send("No upcoming assignments found.")
            return
        
        embed = Embed(
            title="Upcoming Assignments (Next 5 Days)",
            color=nextcord.Color.blurple()
        )

        sorted_assignments = sorted(assignments, key=lambda x: dt.strptime(x.due_at, '%Y-%m-%dT%H:%M:%SZ'))

        for a in sorted_assignments:
            due = dt.strptime(a.due_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
            due_str = due.strftime('%A, %B %d at %I:%M %p UTC')
            embed.add_field(
                name=f"{a.name}",
                value=f"{a.course_name}\nDue: {due_str}",
                inline=False
            )

        await interaction.followup.send(embed=embed)


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
        
        if self.curr_course is None:
            await interaction.followup.send("Please select a course using /courses command before requesting announcements.", ephemeral=True)
            return
        
        user = canvasapi.Canvas(API_URL, api_key)
        announcement_pl  = user.get_announcements(context_codes=[self.curr_course])

        announcements = list(announcement_pl)

        if len(announcements) == 0:
            await interaction.followup.send("No announcements found for this course.", ephemeral=True)
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
            await interaction.followup.send(embed=embed, ephemeral=True)
            break
    
    @nextcord.slash_command(name='coursegrade', description='View your grade for the current course')
    async def get_course_grade(self, interaction: Interaction):
        """
        
        Gets the current grade and letter grade for a specified course. 
        Params:
            interaction : Interaction >> a Discord interaction
            course_number : int >> Index of the course selected by the user
        Return:
            Nothing
        """
        await interaction.response.defer(ephemeral=True)

        API_URL = 'https://templeu.instructure.com/'
        api_key = await self.get_user_canvas(member=interaction.user)

        if api_key == 'Please login using the /login command!':
            await interaction.followup.send(api_key)
            return
        
        user = canvasapi.Canvas(API_URL, api_key)
        courses = list(user.get_courses(enrollment_state='active'))
        
        if self.curr_course is None:
            await interaction.followup.send("Please select a course using /courses command before requesting your grade.", ephemeral=True)
            return
        course = self.curr_course

        try:
            enrollment = course.get_enrollments(user_id='self')[0]
            grade = enrollment.grades.get('current_score', None)

            if grade is None:
                await interaction.followup.send(f"No grade available for **{course.name}**.", ephemeral=True)
                return
            
            grade = round(float(grade), 2)
            letter = self.get_letter_grade(grade)

            await interaction.followup.send(f"**{course.name}**\n{grade}% ({letter})", ephemeral=True)

        except Exception as e:
            print(f"Error fetching grade: {e}")
            await interaction.followup.send("There was an error retrieving the grade. Please try again later.", ephemeral=True)


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


    @nextcord.slash_command(name="semester_gpa", description="View your current weighted GPA for THIS semester.")
    async def get_semester_gpa(self, interaction: Interaction):
        """
        Calculates and diplsays the user's current semester GPA based on active courses.
        
        Args:
            interaction: The Discord interaction
        """
        await interaction.response.defer(ephemeral=True)

        API_URL = 'https://templeu.instructure.com/'
        api_key = await self.get_user_canvas(member=interaction.user)

        if api_key == 'Please login using the /login command!':
            await interaction.followup.send(api_key, ephemeral=True)
            return
        
        try:
            # Connect to Canvas API
            user = canvasapi.Canvas(API_URL, api_key)

            # Get all active courses 
            all_courses = user.get_courses(enrollment_state='active')

            # Try to get detailed course info and identify current courses based on assingments due this month
            print("Getting course info and checking current assingments:")
            current_semester_courses = []
            current_month = dt.now().month
            current_year = dt.now().year
            previous_month = current_month - 1 if current_month > 1 else 12
            previous_month_year = current_year if current_month > 1 else current_year - 1

            for course in all_courses:
                try:
                    print(f"Course: {course.name}")

                    assignments = list(course.get_assignments())
                    has_relevant_assignments = False
                    
                    # Check if any assignments are due this month
                    for assignment in assignments:
                        if hasattr(assignment, 'due_at') and assignment.due_at:
                            try:
                                due_date = dt.strptime(assignment.due_at, '%Y-%m-%dT%H:%M:%SZ')
                                # Check for current month
                                if due_date.year == current_year and due_date.month == current_month:
                                    has_relevant_assignments = True
                                    print(f"   Assignment due in current month: {assignment.name}")
                                    break
                                # Check for previous month
                                elif due_date.year == previous_month_year and due_date.month == previous_month:
                                    has_relevant_assignments = True
                                    print(f"   Assignment due in previous month: {assignment.name}")
                                    break
                            except Exception as e:
                                print(f"  Error parsing due date {e}")
                    
                    # If we found current assignments, add to current semester courses
                    if has_relevant_assignments:
                        current_semester_courses.append(course)
                        print(f"   Added to current semester courses (recent assignments)")
                    else: 
                        print(f"   No assignments due in current or previous month")

                        # Fallback for courses without current assignments but with "2025" in name
                        if '2025' in course.name:
                            current_semester_courses.append(course)
                            print(f"   Added to current semester courses (2025 in name)")
                except Exception as e:
                    print(f"   Error processing course {course.name}: {e}")
        
            if not current_semester_courses:
                await interaction.followup.send("No current semester courses found.", ephemeral=True)
                return
            
            # Calculate GPA
            course_data = []

            for course in current_semester_courses:
                try:
                    # Get enrollment information for this course
                    enrollment = course.get_enrollments(user_id='self')[0]
                    current_score = enrollment.grades.get('current_score')

                    # Skip courses with no grade
                    if current_score is None:
                        continue

                    # Convert percentage grade to 4.0 scale
                    current_score = float(current_score)
                    gpa_points = self.convert_to_gpa_scale(current_score)

                    # Store data for UI selection (not setting credits yet)
                    course_data.append({
                        'name': course.name,
                        'grade': current_score,
                        'gpa_points': gpa_points,
                        'credits': None # Will be filled by user selection
                    })
                except Exception as e:
                    print(f"Error processing course {course.name}: {e}")
                    continue
            
            if not course_data:
                await interaction.followup.send("Could not calculate GPA - no graded courses found for this semester.", ephemeral=True)
                return
            
            await self.create_credit_hour_selection(interaction, course_data)

        except Exception as e:
            print(f"Error calculating semester GPA: {e}")
            await interaction.followup.send("An error occurred while calculating your semester GPA. Please try again later.", ephemeral=True)

def setup(client):
    client.add_cog(stud_util(client))
