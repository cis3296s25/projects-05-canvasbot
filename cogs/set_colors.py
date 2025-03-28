import os
import json
import requests
import nextcord
from nextcord.ext import commands
from nextcord import Interaction
from nextcord.ui import View, Select


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

            async def callback(interaction: Interaction, c = course, s = color_select):
                self.responses[c['id']] = {
                    "name": c['name'],
                    "color": s.values[0]
                }

                await interaction.response.send_message(f"✅ Color for {c['name']} set to {GOOGLE_COLORS[s.values[0]]}.", ephemeral=True)
            
            color_select.callback = callback  # <-- right here!
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
        await interaction.response.defer(ephemeral=True)

        # Get decrypted Canvas token
        canvas_token = await self.client.get_cog("stud_util").get_user_canvas(interaction.user)
        if not canvas_token.startswith("9") and not canvas_token.startswith("1"):
            await interaction.followup.send("❌ Please login using `/login <token>` first.", ephemeral=True)
            return

        # Get list of enrolled courses from Canvas
      
        headers = {"Authorization": f"Bearer {canvas_token}"}
        res = requests.get("https://templeu.instructure.com/api/v1/courses", headers=headers)


        if res.status_code != 200:
            await interaction.followup.send("⚠️ Failed to retrieve Canvas courses.", ephemeral=True)
            return

        courses = res.json()
        if not isinstance(courses, list):
            await interaction.followup.send("⚠️ Unexpected response from Canvas API.", ephemeral=True)
            return

        courses = [c for c in courses if not c.get("access_restricted_by_date")]  # Filter

        if not courses:
            await interaction.followup.send("No active Canvas courses found.", ephemeral=True)
            return
        
        if len(courses) > 5:
            await interaction.followup.send(
                f"⚠️ You have {len(courses)} courses — only the first 25 are shown.",
                ephemeral=True
            )

        # Show color selection menu
        view = ColorPickerView(courses, str(interaction.user.id))
        await interaction.followup.send("🎨 Select a color for each class:", view=view, ephemeral=True)


def setup(client):
    client.add_cog(CanvasColorCog(client))
