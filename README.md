# e-newspaper-dl
`pip install -r requiremnts.txt` to download required packages


## Usage
```
usage: main.py [-h] [--channel_link LINK] [--drive_folder_id ID] [--skip-upload] [--email EMAIL [EMAIL ...]]
               [--add-mail-list EMAIL [EMAIL ...]] [--newspaper NAME [NAME ...]] [--add-newspaper NAME [NAME ...]]

Newspaper PDF Downloader + Dispatcher.
Looks within the telegram-channels for the specified newspaper (file name) 
that were added today and sends an email with the link to the newspaper. When a file is found, it is downloaded 
to the local machine in './tmp' directory. The file is also uploaded to google drive as some attachments above
50mb in size cannot be sent via gmail, they can only be shared through google-drive.

optional arguments:
  -h, --help            show this help message and exit
  --channel_link LINK, -c LINK
                        specify Telegram channel link(s)
  --drive_folder_id ID, -d ID
                        specify Google Drive folder ID, the files will be uploaded to this folder
                        
  --skip-upload         skips uploading to drive if size of file is less than 35mb
  
  --email EMAIL [EMAIL ...], -e EMAIL [EMAIL ...]
                        email address to send too, multiple emails can be specified by separating 
                        them with whitespaces
  --add-mail-list EMAIL [EMAIL ...], -a EMAIL [EMAIL ...]
                        add email address to current mailing list, multiple emails can be specified by separating 
                        them with whitespaces
  --newspaper NAME [NAME ...], -N NAME [NAME ...]
                        newspapers to find in the telegram-channels, multiple newspapers can be specified 
                        by separating them with whitespaces
  --add-newspaper NAME [NAME ...], -n NAME [NAME ...]
                        adds that search query to the current list of newspapers to find

```

Running main.py should mention all it needs/thats missing.

- Prerequisites
  1. Python 3.8 >=
  2. [telegram api credentials](https://core.telegram.org/api/obtaining_api_id) 
  3. Google drive folder id. 
      - ![](https://i.imgur.com/5crtc2M.png)
  4. Client_id.json for OAuth Access (for gmail-api & drive api) 
    - create a new google account (optional); Can use your own... the mails will then be sent through your account.    
    - go to [`console.cloud.google`](https://console.cloud.google.com), create new project
    - enable gmail API & drive API through api library
    - get [`client_id.json`](https://developers.google.com/workspace/guides/create-credentials#oauth-client-id)
      - Choose `desktop application` 
  5. A telegram channel that uploads newspapers daily
