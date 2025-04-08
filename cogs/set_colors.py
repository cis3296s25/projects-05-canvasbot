import os
import json
import requests
import nextcord
from nextcord.ext import commands
from nextcord import Interaction
from nextcord.ui import View, Select
from datetime import datetime, timezone


GOOGLE_COLORS = {
    "1": "Lavender",
    "2": "Sage",
    "3": "Grape",
    "4": "Flamingo",
    "5": "Banana",
    "6": "Tangerine",
    "7": "Peacock",
    "8": "Graphite",
    "9": "Blueberry",
    "10": "Basil",
    "11": "Tomato",
}

class ColorPickerView(View):
    def __init__(self, courses, user_id):
        super().__init__(timeout = 300)
        self.user_id = user_id
        self.courses = courses
        self.responses = {}

        for course in courses[:5]:
            color_select = Select(
                placeholder = f"Pick color for {course['name'][:90]}",
                min_values = 1,
                max_values = 1,
                options = [
                    nextcord.SelectOption(label=name, value=color_id)
                    for color_id, name in GOOGLE_COLORS.items()
                ]
            )

            async def callback(interaction: Interaction, c=course, s=color_select):
                self.responses[c['id']] = {
                    "name": c['name'],
                    "color": s.values[0]
                }

                # Save immediately
                folder = "course_colors"
                os.makedirs(folder, exist_ok=True)
                with open(f"{folder}/{self.user_id}.json", "w") as f:
                    json.dump(self.responses, f, indent=4)

                await interaction.response.send_message(
                    f"✅ Color for {c['name']} set to {GOOGLE_COLORS[s.values[0]]}.",
                    ephemeral=True
                )


            color_select.callback = callback  
            self.add_item(color_select)


    async def on_timeout(self):
        # Save responses to file when view times out
        if not os.path.exists("course_colors"):
            os.makedirs("course_colors")
        with open(f"course_colors/{self.user_id}.json", "w") as f:
            json.dump(self.responses, f, indent=4)        


class CanvasColorCog(commands.Cog):
    def __init__(self, client):
        self.client = client

    @nextcord.slash_command(name="setup_colors", description="Assign calendar colors to your Canvas classes.")
    async def setup_colors(self, interaction: Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
        except nextcord.errors.NotFound:
            print("⚠️ Interaction already expired. Skipping defer.")
            return

        # Get decrypted Canvas token
        canvas_token = await self.client.get_cog("stud_util").get_user_canvas(interaction.user)
        if not canvas_token.startswith("9") and not canvas_token.startswith("1"):
            await interaction.followup.send("❌ Please login using `/login <token>` first.", ephemeral=True)
            return

        # Get list of enrolled courses from Canvas
      
        headers = {"Authorization": f"Bearer {canvas_token}"}
        res = requests.get(
            "https://templeu.instructure.com/api/v1/courses?per_page=100",
            headers=headers
        )


        if res.status_code != 200:
            await interaction.followup.send("⚠️ Failed to retrieve Canvas courses.", ephemeral=True)
            return

        courses = res.json()
        print("---- RAW COURSES ----")
        print(json.dumps(courses, indent=2))

        if not isinstance(courses, list):
            await interaction.followup.send("⚠️ Unexpected response from Canvas API.", ephemeral=True)
            return
        
        # Show only courses that are active + available + not date-restricted
        def is_enrollable_course(course):
            enrollments = course.get("enrollments", [])
            is_enrolled = any(e.get("enrollment_state") == "active" for e in enrollments)
            is_available = course.get("workflow_state") == "available"
            is_restricted = course.get("access_restricted_by_date")
            return is_enrolled and is_available and not is_restricted

        filtered_courses = [c for c in courses if is_enrollable_course(c)]

        # Sort by most recently created (fallback when dates are unreliable)
        filtered_courses = sorted(
            filtered_courses,
            key=lambda c: c.get("created_at", ""),
            reverse=True
        )

        if not filtered_courses:
            await interaction.followup.send("No active Canvas courses found.", ephemeral=True)
            return

        if len(filtered_courses) > 25:
            await interaction.followup.send(
                f"⚠️ You have {len(filtered_courses)} active Canvas courses — only the first 25 are shown.",
                ephemeral=True
            )

        # Limit to 25 max for UI
        filtered_courses = filtered_courses[:25]

        # Show color selection menu
        view = ColorPickerView(filtered_courses, str(interaction.user.id))
        await interaction.followup.send(
            "**🎨 Select a color for each class you'd like to sync to Google Calendar.**\n"
            "Leave any course **blank** if you don't want it to appear on your calendar.",
            view=view,
            ephemeral=True
        )



def setup(client):
    client.add_cog(CanvasColorCog(client))
