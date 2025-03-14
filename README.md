# CanvasBot
CanvasBot is a Discord bot that integrates with the Canvas API to provide a seamless experience for both students and professors. By issuing simple commands, the bot allows students to access their due dates, receive notifications about assignments and deadlines, and recieve announcemets from Canvas all in Discord. Authentication is used to ensure students can safely access their course information through the bot.

#  How to run
Installation is easy! All you need is Discord, a Discord account, and a server. Next, click [here](https://discord.com/api/oauth2/authorize?client_id=1075548726313111594&permissions=2483030064&scope=bot) to invite the bot to any server you have administrator privileges in. The bot is now in your server and is ready to be used. You may also need to give the bot administrator privileges to push notifications and send messages in authorized channels. If everything is set up correctly, you should be able to see and use the commands by typing "/" in Discord text box.

# How to build
If you want to build the bot for yourself, you will need 2 things:
1. A Discord Bot Token: https://www.writebots.com/discord-bot-token/
2. A Canvas API Token: https://kb.iu.edu/d/aaja

After obtaining both of these, put them in a file called .env in the same directory as main. In this file, initialize the Discord token as a string called "DISCORD" and the Canvas token as a string called "CANVAS." Then you can make whatever changes you'd like to the code, and by running main the bot should be up and running!

# Installing Dependencies
Ensure you have Python installed(3.9+). Then, install the required dependencies:

```
pip install -r requirements.txt
```
