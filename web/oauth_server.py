# Flask server to handle OAuth2 callback from Google
# This is where Google redirects the user after login
# It fetches the access token and saves it securely

import os
from dotenv import load_dotenv
load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from flask import Flask, request
from google_auth_oauthlib.flow import Flow
import json


# Create a Flask app instanc
app = Flask(__name__)


# Define the OAuth scopes (permissions)
# This one allows creating and managing events in the user's Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# Redirect URI must match what was set in Google Cloud Console and the Discord bot
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


# This route handles Google's redirect after user logs in
@app.route("/oauth2callback")
def oauth2callback():
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # Allow HTTP for dev
     # Initialize the OAuth flow with the same settings used to generate the original auth URL
    print("REDIRECT_URI =", REDIRECT_URI)
    flow = Flow.from_client_secrets_file(
        "../credentials.json",  # Google OAuth credentials file
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(
        authorization_response=request.url
    )
 # Use the full URL the user was redirected to, which includes the authorization code
    credentials = flow.credentials # Now we have the user's access and refresh tokens


    # Retrieve the original Discord user ID from the state parameter
    # This ties the Google account to the correct Discord user
    user_id = request.args.get("state")  # Came from Discord

    os.makedirs("tokens", exist_ok=True)

    # Save the user's tokens securely to a file named after their Discord ID
    # In production, you should encrypt this or store it in a database
    with open(f"tokens/{user_id}.json", "w") as f:
        json.dump({
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }, f)

    # Return a simple confirmation message in the browser
    return "Your Google Calendar is now connected. You may close this tab."


# Run the Flask app on port 5000 when this script is executed
if __name__ == "__main__":
    app.run(port=5000)
