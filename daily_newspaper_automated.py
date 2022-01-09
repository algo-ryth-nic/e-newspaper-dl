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
file_name = './tmp/newspaper.pdf'


def progress_bar(current, total):
    download_status = f'Downloaded {current} out of {total} bytes'
    done = int(50*current/total)
    print('\r[{}{}] {:.2%} : '.format('█' * done, '.' * (50-done), current / total) + download_status, end = '', flush = True)


def run_telethon_client(session_string, cred, channel_link, newspaper_to_find):
    # starting our telegram client
    with TelegramClient(StringSession(session_string), **cred) as client:

        print('>> Client Started...')

        # name of channel
        channel_name = client.get_entity(channel_link)

        # current date
        current_date = datetime.utcnow()

        print(f'\n[*] Getting the last Chat File Upload for channel: {channel_name.title}')

        # getting last message and checking if any new messages made on the same day yet
        # filter to show only document type media, and using search to find similar file of similar names
        for msg in client.iter_messages(channel_name, filter =InputMessagesFilterDocument, search = newspaper_to_find, limit=2):

            print(msg.document.attributes[0].file_name)

            if msg.date.date() != current_date.date():
                print("\n>> No file have been uploaded today!")
                # this means pdf files have not been uploaded yet (no message made this day yet...)
                break

            # cancel job if size is greater than 200mb
            if not  (msg.document.size > 200*10**6 or msg.document.size < 10*10**6):
                print(f"\n>> File Found, File: {msg.document.attributes[0]}")
                print("\n[*] Downloading File...")
                # that means we found our pdf file
                # we'll download this file, it will override the old file if present in the path
                msg.download_media(file = file_name, progress_callback = progress_bar)

                # disconnecting the client, our job is done
                client.disconnect()
                print("\n>> Client Successfully Disconnected!")
                return True

            else:
                print(f"\n>> File skipped: {msg.document.attributes[0]}; Size: {msg.document.size / 10**6} mb")


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

    channel_link = 'https://t.me/TOI_dailyepaper'
    newspaper_to_find = 'TOI DELHI'

    cli_parser = argparse.ArgumentParser(description = 'Newspaper PDF Scraper + Dispatcher')
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
        help='Email address to send the file to',
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
        '--newspaper', '-n',
        help='Newspapers to find',
        default = newspaper_to_find,
        nargs='+',
        dest='newspaper',
        metavar='NAME',
        type=str
    )

    args = cli_parser.parse_args()

    # assigning values
    channel_link = args.channel_link
    drive_folder_id = args.drive_folder_id
    mailing_list = args.email
    newspaper_to_find = args.newspaper
    if args.additional_emails:
        mailing_list.extend(args.additional_emails)

    # calling main function
    main(channel_link, drive_folder_id, mailing_list, newspaper_to_find)

