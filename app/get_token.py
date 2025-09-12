from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import json

# Calendar scope
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Path to your credentials.json
creds_file = 'credentials.json'

def generate_token():
    flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
    creds = flow.run_local_server(port=0)  # Opens browser for authorization

    # Save token for later use
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    print("✅ token.json generated successfully!")

if __name__ == '__main__':
    generate_token()
