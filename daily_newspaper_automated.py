from telethon.sync import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import InputMessagesFilterDocument
import json
import re
import pickle
from datetime import datetime, timedelta, time
import asyncio
import os
import argparse

from google_oauth import create_service
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64

from googleapiclient.http import MediaFileUpload    # to upload to drive
# from email.mime.application import MIMEApplication

# Gobal variables
# file_name = './tmp/newspaper.pdf'


def progress_bar(current, total):
    download_status = f'Downloaded {current} out of {total} bytes'
    done = int(50*current/total)
    print('\r[{}{}] {:.2%} : '.format('█' * done, '.' * (50-done), current / total) + download_status, end = '', flush = True)


def search_for_file(client, channel, search_query, current_date, file_paths):
    file_name = f"./tmp/{'_'.join( search_query.split(' ') )}.pdf"

    # getting last message and checking if any new messages made on the same day yet
    # filter to show only document type media, and using search to find similar file of similar names
    for msg in client.iter_messages(channel, filter =InputMessagesFilterDocument, search = search_query, limit=2):

        print(msg.document.attributes[0].file_name)

        if msg.date.date() != current_date.date():
            print("\n>> File not been uploaded today!")
            # this means pdf files have not been uploaded yet (no message made this day yet...)
            break

        # cancel job if size is greater than 200mb or less than 10mb
        if not  (msg.document.size > 200*10**6 or msg.document.size < 10*10**6):
            print(f"\n>> File Found, File: {msg.document.attributes[0]}")
            print("\n[*] Downloading File...")
            # that means we found our pdf file
            # we'll download this file, it will override the old file if present in the path
            # msg.download_media(file = file_name, progress_callback = progress_bar)
            
            print("\n[*] File Downloaded!")

            file_paths.append(file_name)
            return True

        else:
            print(f"\n>> File skipped: {msg.document.attributes[0]}; Size: {msg.document.size / 10**6} mb")
    return False


def run_telethon_client(session_string, cred, channel_links, newspapers):
    # starting our telegram client
    with TelegramClient(StringSession(session_string), **cred) as client:

        print('>> Client Started...')

        # current date
        current_date = datetime.utcnow()

        # getting channel (can be multiple)
        channels = client.get_entity(channel_links)

        file_paths = [] 
        newspaper_download = False
        for channel in channels:
            if len(newspapers) == 0:
                break

            print(f'\n[*] Getting the last Chat File Upload for channel: {channel.title}')
            # search for each newspaper and remove that newspaper from the list
            for newspaper_to_find in newspapers[:]:
                if search_for_file(client, channel, newspaper_to_find, current_date, file_paths):
                    newspapers.remove(newspaper_to_find)
                    newspaper_download = True
            
        # disconnecting the client, our job is done
        client.disconnect()
        
    print("\n>> Client Successfully Disconnected!")
    
    # not a single newspaper been downloaded 
    if newspaper_download:
        print(f"\n>> {len(file_paths)} Newspapers files downloaded!")
        return True
    else:
       print("\n[*] No newspapers was found!")
       return False
        



def upload_file_to_drive(folder_id, upload_file_name):
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
    media = MediaFileUpload(file_name, mimetype = 'application/pdf')

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

    # sending...
    message = service.users().messages().send(userId='me', body={'raw': raw_string}).execute()

    print(f"\n[gmail-Service] {message}")


def main(channel_link, drive_folder_id, mailing_list, newspaper_to_find):
    print("Script has started running")
    # event is <dict>

    # --------------------------------------- Getting All Credentials for telegram ------------------------------

    # getting api credentials for telethon
    cred = {}
    with open('api_credentials.json', 'r') as f:
        cred = json.loads(f.read())

    # getting auth-key session string
    auth_key = None
    with open('aws-lambda-toi-session.pickle', 'rb') as f:
        auth_key = pickle.load(f)

    # ---------------------------------------------------------

    # telegram channel link
    print(channel_link)

    # start telegram scraper
    status = run_telethon_client(auth_key, cred, channel_link, newspaper_to_find)

    if status:

        if os.path.exists(file_name):
            current_date = datetime.utcnow() + timedelta(hours = 5, minutes = 30)

            # uploading to drive
            # FOLDER ID
            folder_id = drive_folder_id
            new_file_name = "TOI-DELHI-" + current_date.strftime("%d-%m-%y")

            link = upload_file_to_drive(folder_id, new_file_name)

            print(f"\n[*] File: {file_name}\nSize: {os.path.getsize(file_name)/10**6} mb\n[*] Successfully Uploaded!")

            # sending email
            to = mailing_list

            subject = "TOI DELHI " + current_date.strftime("%d/%m/%y")
            body =f"""The Times of India (Delhi) newspaper for \"{current_date.strftime("%A, %B %d, %Y")}\" will be found below along with the link to it.\n
Link to newspaper: {link}

For any problems, contact me.

This is an automated message... Please don't reply to this email.
            """

            send_email_using_gmailAPI(to, subject, body)

            print("\n[*] Success!")

        else:
            print(f"\n[*] Path doesn\'t exist; {file_name}")

    else:
        print("\n\n>> Email couldn\'t be prepared, since Client wasn\'t able to find the pdf file")


if __name__ == "__main__":
    drive_folder_id = ""
    mailing_list = [ ]

    channel_link = ['https://t.me/TOI_dailyepaper', 'https://t.me/EnewsPaperEarly']
    newspaper_to_find = ['TOI DELHI']

    cli_parser = argparse.ArgumentParser(description = 'Newspaper PDF Downloader + Dispatcher')
    cli_parser.add_argument(
        '--channel_link', '-c',
        help='Specify Telegram channel link',
        default = channel_link,
        dest='channel_link',
        metavar='LINK',
        type=str
    )
    cli_parser.add_argument(
        '--drive_folder_id', '-d',
        help='Specify Google Drive folder ID to upload the file',
        default = drive_folder_id,
        dest='drive_folder_id',
        metavar='ID',
        type=str
    )
    cli_parser.add_argument(
        '--skip-upload',
        help='Skip uploading to drive if size of file is less than 35mb',
        action='store_true',
        dest='skip_upload',
        default=False
    )

    cli_parser.add_argument(
        '--email', '-e',
        help='Email address to send too',
        default = mailing_list,
        nargs='+',
        dest='email',
        type=str
    )
    cli_parser.add_argument(
        '--add-mail-list', '-a',
        help='Add email address to current mailing list',
        type=str,
        nargs='+',
        dest='additional_emails',
        metavar='EMAIL'
    )
    cli_parser.add_argument(    
        '--newspaper', '-N',
        help='Newspapers to find',
        default = newspaper_to_find,
        nargs='+',
        dest='newspaper',
        metavar='NAME',
        type=str
    )
    cli_parser.add_argument(
        '--add-newspaper', '-n',
        help='Adds that search query to the list of newspapers to find',
        type=str,
        nargs='+',
        dest='additional_newspapers',
        metavar='NAME'
    )

    args = cli_parser.parse_args()

    # assigning values
    channel_link = args.channel_link
    drive_folder_id = args.drive_folder_id
    mailing_list = args.email
    newspaper_to_find = args.newspaper
    if args.additional_emails:
        mailing_list.extend(args.additional_emails)

    if args.additional_newspapers:
        newspaper_to_find.extend(args.additional_newspapers)

    # for debugging 
    print(f'{channel_link=}, {drive_folder_id=}, {mailing_list=}, {newspaper_to_find=}')

    # calling main function
    main(channel_link, drive_folder_id, mailing_list, newspaper_to_find)

