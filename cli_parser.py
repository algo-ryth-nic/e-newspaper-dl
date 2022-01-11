import argparse

def parse_cli_args(channel_link, drive_folder_id, mailing_list, look_for):
    cli_parser = argparse.ArgumentParser(
        description = "Newspaper PDF Downloader + Dispatcher.Looks within the telegram-channels for the specified \
            newspaper (file name) that were added today and sends an email with the link to the newspaper. \
            When a file is found, it is downloaded to the local machine in './tmp' directory. The file is also uploaded to google drive as some attachments above 50mb in size\
            cannot be sent via gmail, they can only be shared through google-drive.")
    cli_parser.add_argument(
        '--channel_link', '-c',
        help='specify Telegram channel link(s)',
        default = channel_link,
        dest='channel_link',
        metavar='LINK',
        type=str
    )
    cli_parser.add_argument(
        '--drive_folder_id', '-d',
        help='specify Google Drive folder ID, the files will be uploaded to this folder',
        default = drive_folder_id,
        dest='drive_folder_id',
        metavar='ID',
        type=str
    )
    cli_parser.add_argument(
        '--skip-upload',
        help='skips uploading to drive if size of file is less than 35mb',
        action='store_true',
        dest='skip_upload',
        default=False
    )

    cli_parser.add_argument(
        '--email', '-e',
        help='email address to send too, multiple emails can be specified by separating them with whitespaces',
        default = mailing_list,
        nargs='+',
        dest='email',
        type=str
    )
    cli_parser.add_argument(
        '--add-mail-list', '-a',
        help='add email address to current mailing list, multiple emails can be specified by separating them with whitespaces',
        type=str,
        nargs='+',
        dest='additional_emails',
        metavar='EMAIL'
    )
    cli_parser.add_argument(    
        '--newspaper', '-N',
        help='newspapers to find in the telegram-channels, multiple newspapers can be specified by separating them with whitespaces',
        default = look_for,
        nargs='+',
        dest='newspaper',
        metavar='NAME',
        type=str
    )
    cli_parser.add_argument(
        '--add-newspaper', '-n',
        help='adds that search query to the current list of newspapers to find',
        type=str,
        nargs='+',
        dest='additional_newspapers',
        metavar='NAME'
    )
    
    args = cli_parser.parse_args()

    return args