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

    def get_course_credits(self, course_name: str) -> int:
        """
        Returns the number of credits for a course based on its name.
        
        Args:
            course_name: The name of the course
            
        Returns:
            int: Number of credits (default is 3)
        """
        # Convert to lowercase for case-insensitive matching
        name_lower = course_name.lower()
        
        # List of (some) courses that are 4 credits
        four_credit_courses = [
            "calculus iii",
            "calculus ii",
            "computer systems",
            "low-level programming",
            "software design",
            "mathematical concepts",
            "data structures",
            "operating systems",
            "systems programming"
            "web application"
            "wireless networks"
            "mobile application"
            "database systems"
        ]
        
        # Check if any of the 4-credit course keywords are in the course name
        for course_keyword in four_credit_courses:
            if course_keyword in name_lower:
                return 4
                
        # Default for other courses
        return 3

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
                    if apiKey:
                        return apiKey
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

    @nextcord.slash_command(name="semester_gpa", description="View your current weighted GPA for THIS semester.")
    async def get_semester_gpa(self, interaction: Interaction):
        """
        Calculates and diplsays the user's current semester GPA based on active courses.
        
        Args:
            interaction: The Discord interaction
        """
        await interaction.response.defer()

        API_URL = 'https://templeu.instructure.com/'
        api_key = await self.get_user_canvas(member=interaction.user)

        if api_key == 'Please login using the /login command!':
            await interaction.followup.send(api_key)
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
                await interaction.followup.send("No current semester courses found.")
                return
            
            # Calculate GPA
            total_points = 0 
            total_credits = 0
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

                    # Get credits based on course name
                    credits = self.get_course_credits(course.name) 

                    # Add to running totals 
                    total_points += gpa_points * credits
                    total_credits += credits

                    # Store for detailed output
                    course_data.append({
                        'name': course.name,
                        'grade': current_score,
                        'gpa_points': gpa_points,
                        'credits': credits
                    })
                except Exception as e:
                    print(f"Error processing course {course.name}: {e}")
                    continue
            
            # Calculate final GPA
            if total_credits > 0:
                semester_gpa = total_points / total_credits
                semester_gpa_rounded = round(semester_gpa, 2)

                # Format output
                output = f"**Your current semester GPA is: {semester_gpa_rounded}**\n\n"
                output += "Course breakdown:\n"
                for c in course_data:
                    output += f"- {c['name']}: {c['grade']}% ({c['gpa_points']} GPA points)\n"

                await interaction.followup.send(output)
            else:
                await interaction.followup.send("Could not calculate GPA - no graded courses found for this semester")

        except Exception as e:
            print(f"Error calculating semester GPA: {e}")
            await interaction.followup.send("An error occurred while calculating your semester GPA. Please try again later.")

def setup(client):
    client.add_cog(stud_util(client))
