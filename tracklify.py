from __future__ import print_function

import os.path
import base64
import gi
import json
import re
from bs4 import BeautifulSoup
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def main():
    subjects = []
    links = []
    
    class EmailListWindow(Gtk.Window):
        def __init__(self):
            Gtk.Window.__init__(self, title="Tracklify")

            self.set_border_width(10)
            self.set_default_size(400, 300)

            # Create a vertical box layout
            self.box = Gtk.VBox()
            self.add(self.box)

            # Add a Refresh button
            self.refresh_button = Gtk.Button(label="Refresh")
            self.refresh_button.connect("clicked", self.load_emails)
            self.box.pack_start(self.refresh_button, False, False, 0)
            

        def load_emails(self, widget):
            creds = None
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())

            try:
                service = build('gmail', 'v1', credentials=creds)

                search_word = "assessment"
                search_query = f"subject:{search_word} OR " \
                            f"body:{search_word} OR " \
                            f"subject:{search_word} OR " \
                            f"body:{search_word} OR "
                
                results = service.users().messages().list(userId='me', q=search_query).execute()
                messages = results.get('messages', [])

                if not messages:
                    print(f'No emails containing "{search_word}" found.')
                    return
                
                print(f'Emails containing "{search_word}":')
                for message in messages:
                    msg = service.users().messages().get(userId='me', id=message['id']).execute()
                    headers = msg['payload']['headers']
                    subject = next((header['value'] for header in headers if header['name'] == 'Subject'), None)
                    if subject:
                        subjects.append(subject)
                        print('Subject:', subject)
                    else:
                        print('Subject not found for message ID:', message['id'])
                    #print(json.dumps(msg, indent = 4))
                    plain_text = ""
                    if 'parts' in msg['payload']:
                        plain_text_part = None
                        for part in msg['payload']['parts']:
                            if part['mimeType'] == 'text/plain':
                                plain_text_part = part
                                break
                        if plain_text_part:
                            encoded_text = plain_text_part['body']['data']
                            decoded_text = base64.urlsafe_b64decode(encoded_text).decode("utf-8")                        
                            soup = BeautifulSoup(decoded_text, 'html.parser')
                            plain_text = soup.get_text(separator=' ')
                            print(plain_text)
                        else:
                            print("No plain text part found in the email.")
                    else:
                        if 'body' in msg['payload']:
                            encoded_text = msg['payload']['body']['data']
                            decoded_text = base64.urlsafe_b64decode(encoded_text).decode("utf-8")
                            soup = BeautifulSoup(decoded_text, 'html.parser')
                            plain_text = soup.get_text(separator=' ')
                            print(plain_text)
                        else:
                            print("No plain text body found in the email.")
                            
                    def extract_links(text):
                        url_pattern = re.compile(r'https?://\S+|www\.\S+')
                        links = re.findall(url_pattern, text)
                        return links
                    
                    linkTemp = extract_links(plain_text)
                    linkString = "\n".join(linkTemp)
                    links.append(linkString)
                        
            except HttpError as error:
                print(f'An error occurred: {error}')
                
            self.grid = Gtk.Grid()
            self.box.pack_start(self.grid, True, True, 0)
            for i, subject in enumerate(subjects):
                label = Gtk.Label(label=subject)
                label.set_alignment(0, 0.5) 
                checkbox = Gtk.CheckButton()
                self.grid.attach(checkbox, 0, i, 1, 1)
                self.grid.attach(label, 1, i, 1, 1)
               
               
            for i, link in enumerate(links):
                print(link)
                linkLabel = Gtk.Label(label=str(link))
                linkLabel.set_alignment(0, 0.5)
                self.grid.attach(linkLabel, 2, i, 1, 1)
                
            self.grid.show_all()

        def on_button_clicked(self, widget):
            print("Selected subjects:")
            for i, subject in enumerate(subjects):
                checkbox = self.grid.get_child_at(0, i)
                if checkbox.get_active():
                    print(subject)

    win = EmailListWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == '__main__':
    main()