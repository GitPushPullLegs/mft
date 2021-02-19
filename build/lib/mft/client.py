import time
import xml.etree.ElementTree as ET
from collections import deque
from datetime import datetime, timedelta
from urllib.parse import urlsplit, unquote, urljoin, quote
import urllib3
import os
import enum
import warnings

import requests


class Client:
    _HEADERS = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"}

    def __init__(self, host: str):
        """
        Creates a client for SolarWinds Serv-U Managed File Transfer (MFT).
        :param host: Usually the URL to the login page.
        """
        self.session = requests.session()
        self.visit_history = deque(maxlen=10)
        self.host = host

    def login(self, username: str, password: str):
        """
        Logs into MFT.
        :param username: Your username.
        :param password: Your password.
        """
        self.credentials = {
            'user': username,
            'pword': password,
            'language': 'en,US',
            'viewshare': ''
        }
        self.session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.session.headers.update(self._HEADERS)
        self.session.hooks['response'].append(self._event_hooks)
        try:
            self.connection_status = self._login()
        except RecursionError as exc:
            print(exc)

    def _login(self):
        self.session.get(self.host)
        return self.visit_history[-1].status_code == 200

    def _event_hooks(self, r, *args, **kwargs):
        path = urlsplit(r.url)[2]
        print(r.url, r.status_code)
        if path == '/' and r.status_code == 200:
            self.session.cookies.update(r.cookies.get_dict())
            params = {
                'Command': 'Login',
                'Sync': int(time.time())
            }
            response = self.session.post(urljoin(self.host, fr"Web%20Client/Login.xml"),
                                         data=self.credentials, params=params)
            if ET.fromstring(response.text).find(".//result").text != '0':
                raise ConnectionRefusedError("Invalid credentials.")
        elif path == '/Web%20Client/Login.xml' and r.status_code == 200:
            self.session.get(urljoin(self.host, r"Web%20Client/Share/Console.htm"))
            self.csrf_token = ET.fromstring(r.text).find(".//CsrfToken").text
            self.session.headers.update({'X-CSRF-Token': self.csrf_token})
            self.session.cookies.update(r.cookies.get_dict())
        else:
            self.visit_history.append(r)
            return r

    class ShareType(enum.Enum):
        request = 0
        send = 1

    def create_file_share(self, share_type: ShareType, files: [str] = None,
                          expiry: int = int((datetime.now() + timedelta(days=30)).timestamp()),
                          password: str = None, subject: str = "File Share", comments: str = None) -> str:
        """
        Uploads the files to the MFT server and returns the URL to be shared with the recipient.
        :param share_type: Whether you are requesting files or sending them.
        :param comments: A comment to attach to the file share.
        :param subject: The subject of the file share.
        :param files: A list of the files to be shared with this link.
        :param expiry: A timestamp for when the files should expire; defaults to a month away.
        :param password: An optional password to protect the files.
        :return: The link to the files.
        """
        if share_type is Client.ShareType.send and (not files or not isinstance(files, list)):
            raise AttributeError("If sending files, the files parameter must contain a list of files.")
        elif share_type is Client.ShareType.request and files:
            warnings.warn("You are requesting files but submitted files. They will be ignored.")

        data = self._create_file_share(share_type=share_type.value, subject=subject, comments=comments, expiry=expiry,
                                       password=password)
        if share_type is Client.ShareType.send:
            self._upload_files(files=files, token=data['token'])
        return data['url']

    def _create_file_share(self, share_type: int, subject: str, comments: str, expiry: int, password: str = None):
        """Creates a file share in MFT and returns the url and token. Expiration defaults to a month from run."""
        payload = {
            "ShareType": share_type,
            "RecipientEmailAddress": "",
            "SenderName": self.credentials['user'].split("@")[0],
            "SenderEmail": self.credentials['user'],
            "NotifyUserOnGuestTransfer": 1,
            "SenderCarbonCopy": 0,
            "EmailSubject": subject,
            "EmailBody": "" if not comments else comments,
            "ExpirationTimestamp": expiry,
            "PasswordIsSet": 0 if not password else 1,
            "Password": '' if not password else password,
            "IncludePasswordInEmail": 0,
            "MaxFileSize": 0
        }
        params = {
            'Command': 'CreateFileShare'
        }

        response = self.session.post(
            urljoin(self.host, r"Web%20Client/Share/CreateFileShare.xml"), data=payload, params=params)
        root = ET.fromstring(response.text)
        return {"url": unquote(root.find(".//ShareURL").text),  # ShareURL Encoded
                "token": root.find(".//ShareToken").text}

    def _upload_files(self, files: [str], token: str):
        """Uploads the files to the previously created file share."""
        params = {
            'Command': 'UploadFileShare',
            'ShareToken': token,
            'IsVirtual': 0,
            'CsrfToken': self.csrf_token
        }
        for index, file in enumerate(files):
            params['TransferID'] = index + 1
            params['File'] = quote(os.path.split(file)[-1])
            self.session.post(urljoin(self.host,
                                      fr"Web%20Client/Share/MultipleFileUploadResult.htm"),
                              files={"file": open(file, 'rb')}, params=params)

    def cancel_file_share(self, share_token: str):
        """Invalidates a file share."""
        params = {
            'Command': 'DeleteFileShare',
            'ShareToken': share_token,
            'Sync': int(time.time())
        }
        response = self.session.post(urljoin(self.host, fr"Web%20Client/Result.xml"), params=params)
        return ET.fromstring(response.text).find(".//ResultText").text

    def list_file_shares(self, count: int = 10):
        """
        Lists the number of file shares specified.
        :param count: Number of file shares to return. Default is 10.
        :return: A list of file share datum.
        """
        payload = {
            'ShareType': 1,
            'NumShares': count,
            'StartPos': 0
        }
        params = {
            'Command': 'ListFileShares',
            'Sync': int(time.time())
        }
        response = self.session.post(urljoin(self.host, fr"Web%20Client/Share/ListFileShares.xml"), data=payload,
                                     params=params)
        root = ET.fromstring(response.text).findall(".//share")
        notification_status = {
            '0': 'Pending',
            '1': 'Sent',
            '2': 'Error Sending',
            '3': 'Downloaded',
            '4': 'Received',
            '5': 'Expired'
        }

        file_shares = []
        for datum in root:
            file_shares.append({
                "share_token": datum.find(".//ShareToken").text,
                "has_password": True if datum.find(".//HasPassword").text == '1' else False,
                "date_created": datetime.fromtimestamp(int(datum.find(".//DateCreated").text)).strftime("%m/%d/%Y"),
                "message_subject": unquote(datum.find(".//MsgSubject").text),
                "first_recipient": datum.find(".//FirstRecipient").text,
                "number_of_recipients": datum.find(".//NumRecipients").text,
                "notification_status": notification_status[datum.find(".//NotificationStatus").text],
                "total_file_size": datum.find(".//TotalFileSize").text,
                "number_of_files": datum.find(".//NumFiles").text,
                "date_of_expiration": datetime.fromtimestamp(int(datum.find(".//DateExpiration").text)).strftime("%m/%d/%Y")
            })

        return file_shares