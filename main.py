from telethon.client import auth
from telethon.sync import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import InputMessagesFilterDocument
import json
import re
import pickle
from datetime import datetime, timedelta, time
import asyncio
import os

from google_oauth import create_service
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64

from googleapiclient.http import MediaFileUpload    # to upload to drive

from cli_parser import parse_cli_args

# Gobal variables
# file_name = './tmp/newspaper.pdf'


def progress_bar(current, total):
    download_status = f'Downloaded {current} out of {total} bytes'
    done = int(50*current/total)
    print('\r[{}{}] {:.2%} : '.format('█' * done, '.' * (50-done), current / total) + download_status, end = '', flush = True)


def search_for_file(client, channel, search_query, current_date, file_paths):
    file_name = f"./tmp/{'-'.join( search_query.upper().split(' ') )}.pdf"

    # getting last message and checking if any new messages made on the same day yet
    # filter to show only document type media, and using search to find similar file of similar names
    for msg in client.iter_messages(channel, filter =InputMessagesFilterDocument, search = search_query, limit=2):
            
        if msg.date.date() != current_date.date():
            print("\n>> File not been uploaded today!")
            # this means pdf files have not been uploaded yet (no message made this day yet...)
            break

        # cancel job if size is greater than 200mb or less than 10mb
        if not  (msg.document.size > 200*10**6 or msg.document.size < 10*10**6):
            print(f"\n[!] {msg.document.attributes[0].file_name} [{msg.document.size/10**6:.2f}mb] File Found! ")
            print("[*] Downloading File...")
            # that means we found our pdf file
            # we'll download this file, it will override the old file if present in the path
            msg.download_media(file = file_name, progress_callback = progress_bar)
            
            print("\n[*] File Downloaded!")

            file_paths.append(file_name)
            return True

        else:
            print(f">> File skipped: {msg.document.attributes[0]}; Size: {msg.document.size / 10**6} mb")
    return False


def run_telethon_client(session_string, cred, channel_links, newspapers):
    # starting our telegram client
    with TelegramClient(StringSession(session_string), **cred) as client:

        print(f'\n>> Client Started... Successfully logged in as {client.get_me().first_name}')

        # current date
        current_date = datetime.utcnow()

        # getting channel (can be multiple)
        channels = client.get_entity(channel_links)

        # outputs...
        print(f'>> Current Date:', current_date.strftime('%d-%m-%Y'))
        print(f'>> Getting Channel: {[c.title for c in channels]}')

        file_paths = [] 
        newspaper_download = False
        for channel in channels:
            if len(newspapers) == 0:
                break

            print(f'\n[*] Channel: {channel.title}')
            
            # search for each newspaper and remove that newspaper from the list
            for newspaper_to_find in newspapers[:]:

                print(f'>> Searching for \"{newspaper_to_find}\"')
                
                if search_for_file(client, channel, newspaper_to_find, current_date, file_paths):
                    newspapers.remove(newspaper_to_find)
                    newspaper_download = True
            
        # disconnecting the client, our job is done
        client.disconnect()
        
    print("\n>> Client Successfully Disconnected!")
    
    # not a single newspaper been downloaded 
    if newspaper_download:
        print(f"[!] {len(file_paths)} Newspapers files downloaded!")
        return (True, file_paths)
    else:
       print("\n[!] No newspapers was found!")
       return (False, None)
        



def upload_file_to_drive(folder_id, upload_file_name, file_path):
    # creating the service
    CLIENT_SECRET_FILE = 'client_id.json'
    API_NAME = 'drive'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/drive']

    service = create_service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

    # creating meta-data for the file
    file_metadata = {
        'name' : upload_file_name,
        'parents' : [folder_id]
    }

    # uploading to drive
    media = MediaFileUpload(file_path, mimetype = 'application/pdf')

    response = service.files().create(
            body = file_metadata,
            media_body = media,
            fields = 'webViewLink, id'
        ).execute()

    file_id = response['id']

    service.permissions().create(
            body={"role":"reader", "type":"anyone"},
            fileId=file_id
        ).execute()

    # sharable_link = f"https://drive.google.com/file/d/{}/view?usp=sharing"
    sharable_link = response.get('webViewLink')
    print(f"\n[*] Link: {sharable_link}")

    return sharable_link


def send_email_using_gmailAPI(To, Subject, Body):
    # creating the service
    CLIENT_SECRET_FILE = 'client_id.json'
    API_NAME = 'gmail'
    API_VERSION = 'v1'
    SCOPES = ['https://mail.google.com/']

    service = create_service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

    # creating message
    msg = MIMEMultipart()
    msg['to'] =  ",".join(To)
    msg['subject'] = Subject

    msg.attach(MIMEText(Body, 'plain'))


    raw_string = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    # status updates
    print(f"""\n---------------- Message Created -----------------\n
                To: {msg['to']}\n
                Subject: {msg['subject']}\n
                Body: \n{Body}\n""")

    print('[gmail-Service] Preparing to send...')
    print(f'[gmail-Service] Sending to addresses: {To}')

    # sending...
    message = service.users().messages().send(userId='me', body={'raw': raw_string}).execute()

    print(f"\n[gmail-Service] {message}")


def generate_new_string_session(cred):
    # creates session in memory and is then stored as a string                      
    # this is the most portable way to use the application,
    # we just need to pass string next time to use login into the same session                      
    # nothing will be cached in the memory, so the session will be lost when the app is closed
    # we will store this session_string in session.pickle for later use  
    
    session = ""
    with TelegramClient(StringSession(), **cred) as client:                     
        session = client.session.save()    
        # save this session string in a telegram_session.pickle file
        with open('session.pickle', 'wb') as f:
            pickle.dump(session, f)
        client.disconnect()

    return session


def get_cred():
    # getting api credentials for telethon
    telegram_cred = {}

    try:
        with open('api_credentials.json', 'r') as f:
            telegram_cred = json.loads(f.read())
            print(">> Credentials Loaded!")

    except FileNotFoundError:   
        print("\n[*] No api credentials for telegram found!")
        print("[*] Please create a file named 'api_credentials.json' with the following structure:")
        print("""
        {
           "api_id" : "<your_api_id>",
	   "api_hash" : "<your_api_hash>"
        }
        """)
        exit()

    # getting auth-key session string
    session_string = None
    try:
        with open('session.pickle', 'rb') as f:
            session_string = pickle.load(f)
            
            # if session_string is None, we need to generate a new one
            if session_string is None:
                raise FileNotFoundError()

            print(">> Session Loaded!")

    except FileNotFoundError:
        print("\n[*] No session found!")
        session_string = generate_new_string_session(telegram_cred)
        print(">> Session Created!")


    return telegram_cred, session_string


def main(channel_link, drive_folder_id, mailing_list, newspapers_to_find, skip_upload):
    print(">> Script started running!")

    # ---- Getting All Credentials for telegram ----
    cred, auth_key = get_cred()

    
    # start telegram scraper
    status = run_telethon_client(auth_key, cred, channel_link, newspapers_to_find)

    if status[0]:
        # for each file in the list
        for file_path in status[1]:
            
            if os.path.exists(file_path):
                current_date = datetime.utcnow() + timedelta(hours = 5, minutes = 30)

                name = os.path.basename(file_path)[:-4]
                file_size = os.path.getsize(file_path)/10**6


                # uploading to drive
                link = None

                # Skip uploading to drive if size of file is less than 35mb
                if file_size > 35 or not skip_upload:
                    # FOLDER ID
                    folder_id = drive_folder_id
                    new_file_name = name.upper()+ '-' + current_date.strftime("%d-%m-%y")

                    print(f"\n>> Preparing file upload to drive...")
                    print(f"[*] File: {file_path}, Size: {file_size:.2f} mb")
                    link = upload_file_to_drive(folder_id, new_file_name, file_path)

                    print(f"[*] Successfully Uploaded!\n")
                else:
                    print(f"[*] File: {file_path}, Size: {file_size:.2f} mb\n[*] Skipped Uploading!\n")
                
                # link of the file if it was uploaded to drive, later added to body of email
                msg_drive_link = "Link to the Newspaper: " + link if link else "\n"


                # sending email
                print(">> Preparing to send email...")
                to = mailing_list
                subject = name.upper() + " " + current_date.strftime("%d/%m/%y")
                body =f"""{name.upper()} newspaper for \"{current_date.strftime("%A, %B %d, %Y")}\" will be found below along with the link to it.\n
    {msg_drive_link}

    For any problems, contact me.

    This is an automated message... Please don't reply to this email.
                """

                send_email_using_gmailAPI(to, subject, body)

                print("\n[*] Success!")

            else:
                print(f"\n[*] Path doesn\'t exist; {file_path}")

    else:
        print("\n\n>> Email couldn\'t be prepared, since Client wasn\'t able to find the pdf file")


if __name__ == "__main__":

    # ---- Default values; for automation (aws lambda, cron, etc...) ----
    drive_folder_id = ""
    mailing_list = [ ]

    channel_link = []
    look_for = []

    # ---- Parsing Arguments ----
    args = parse_cli_args(channel_link, drive_folder_id, mailing_list, look_for)

    # assigning values
    channel_link = args.channel_link
    drive_folder_id = args.drive_folder_id
    mailing_list = args.email
    look_for = args.newspaper
    if args.additional_emails:
        mailing_list.extend(args.additional_emails)

    if args.additional_newspapers:
        look_for.extend(args.additional_newspapers)


    # for debugging 
    print(f'[?] Default Settings\n{channel_link=}, {drive_folder_id=}, {mailing_list=}, {look_for=}\n')

    # if either drive_folder_id, channel_link, look_for & mailing_list are empty, then exit
    if not (drive_folder_id and channel_link and look_for and mailing_list): 
        print("[*] Please specify all of the following:")
        print("\t1. Google Drive Folder ID")
        print("\t2. Telegram Channel Link(s)")
        print("\t3. Newspapers to look for")
        print("\t4. Email address to send too")
        print('for more information, run the script with --help or -h\n')
        exit()

    # calling main function
    main(channel_link, drive_folder_id, mailing_list, look_for, skip_upload=args.skip_upload)

