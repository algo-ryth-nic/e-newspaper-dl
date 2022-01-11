# e-newspaper-dl
`pip install -r requiremnts.txt` to download required packages


## Usage
```
usage: main.py [-h] [--channel_link LINK] [--drive_folder_id ID] [--skip-upload] [--email EMAIL [EMAIL ...]]
               [--add-mail-list EMAIL [EMAIL ...]] [--newspaper NAME [NAME ...]] [--add-newspaper NAME [NAME ...]]

Newspaper PDF Downloader + Dispatcher.Looks within the telegram-channels for the specified newspaper (file name) that were added
today and sends an email with the link to the newspaper. When a file is found, it is downloaded to the local machine in './tmp'
directory. The file is also uploaded to google drive as some attachments above 50mb in size cannot be sent via gmail, they can
only be shared through google-drive.

optional arguments:
  -h, --help            show this help message and exit
  --channel_link LINK, -c LINK
                        specify Telegram channel link(s)
  --drive_folder_id ID, -d ID
                        specify Google Drive folder ID, the files will be uploaded to this folder
  --skip-upload         skips uploading to drive if size of file is less than 35mb
  --email EMAIL [EMAIL ...], -e EMAIL [EMAIL ...]
                        email address to send too, multiple emails can be specified by separating them with whitespaces
  --add-mail-list EMAIL [EMAIL ...], -a EMAIL [EMAIL ...]
                        add email address to current mailing list, multiple emails can be specified by separating them with
                        whitespaces
  --newspaper NAME [NAME ...], -N NAME [NAME ...]
                        newspapers to find in the telegram-channels, multiple newspapers can be specified by separating them
                        with whitespaces
  --add-newspaper NAME [NAME ...], -n NAME [NAME ...]
                        adds that search query to the current list of newspapers to find

```
