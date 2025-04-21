## CanvasBot

CanvasBot is a Discord bot that integrates with the Canvas API to provide a seamless experience for both students and professors. With simple slash commands, users can access upcoming due dates, course grades with a what-if option, receive assignment reminders, view announcements, and manage their Canvas courses — all directly within Discord. Authentication ensures that each user's course information remains secure. You can also link your courses to a dynamic calendar that automatically updates with assignment deadlines and important dates.

## How to Run

You can either host the bot yourself by following the steps below, or [click here](https://discord.com/oauth2/authorize?client_id=1326788185577226250) to invite an existing instance of the bot to your server.

Whether you host it yourself or use the invite link, you’ll still need to generate a Canvas API token (see the steps in the "How to Build" section) and use the `/login` command to authenticate.

## How to Build

If you want to build the bot for yourself, you'll need two things: a **Discord Bot Token** and a **Canvas API Token**.

### Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application.  
2. Navigate to the **Bot** section and click **Reset Token** to grab your token.  
3. Enable all 3 **Privileged Gateway Intents**:  
   - Presence Intent  
   - Server Members Intent  
   - Message Content Intent  
4. Under **Installation -> Default Install Settings**, select the following:  
   - **Guild Install Scopes**: `bot`  
   - **Bot Permissions**: `Administrator`  
5. Use the install URL to invite the bot to your server.  
6. Run the bot once to auto-generate the necessary config files.  
7. In the root directory, enter your bot token in the .env file.
   
### Canvas API Token

1. Log into Canvas.  
2. On the left-hand sidebar, click **Account**.  
3. In the Account menu, select **Settings**.  
4. Scroll down to the **Approved Integrations** section and click **+ New Access Token**.  
5. Fill out the required fields and click **Generate Token**.  
6. Copy the generated token — you’ll use it with the `/login` command in Discord.

# Installing Dependencies
Ensure you have Python installed (3.8+). Then, install the required dependencies:

```
pip install -r requirements.txt
```


