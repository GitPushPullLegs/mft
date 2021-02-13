import re
import time
from collections import deque
from urllib.parse import urlsplit, unquote, urljoin
from datetime import datetime, timedelta

import requests


class Client:
    _HEADERS = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"}

    def __init__(self, host: str):
        self.host = host

    def login(self, username: str, password: str):
        self.credentials = {
            'user': username,
            'pword': password,
            'language': 'en,US',
            'viewshare': ''
        }
        self.visit_history = deque(maxlen=10)
        self.session = requests.session()
        self.session.headers.update(self._HEADERS)
        self.session.hooks['response'].append(self._event_hooks)
        try:
            self.connection_status = self._login()
        except RecursionError as exc:
            print(exc)

    def _login(self):
        self.session.get(self.host)
        return self.visit_history[-1].status_code == 200 and self.visit_history[-1].url == self.host


    def _event_hooks(self, r ,*args, **kwargs):
        scheme, netloc, path, query, frag = urlsplit(r.url)
        print(r.url, r.status_code)
        if path == '/' and r.status_code == 200:
            self.session.cookies.update(r.cookies.get_dict())
            self.session.post(urljoin(self.host, fr"Web%20Client/Login.xml?Command=Login&Sync={int(time.time())}"), data=self.credentials)
        elif path == '/Web%20Client/Login.xml' and r.status_code == 200:
            self.session.get(urljoin(self.host, r"Web%20Client/Share/Console.htm"))
            self.csrf_token = re.findall(r"(?<=<CsrfToken>)[\W\w]+(?=<\/CsrfToken>)", r.text)[0]
            self.session.cookies.update(r.cookies.get_dict())
        else:
            self.visit_history.append(r)
            return r

    def upload_files(self, files: [str], expiry: int = int((datetime.now() + timedelta(days=30)).timestamp()), password: str = None):
        """Uploads the files to the MFT server and returns the URL to be shared with the recipient."""
        data = self._create_file_share(expiry=expiry, password=password)
        url = unquote(data['url'])
        token = data['token']
        self._upload_files(files=files, token=token)
        return url

    def _create_file_share(self, expiry: int, password: str = None):
        """Creates a file share in MFT and returns the url and token. Expiration defaults to a month from run."""
        self.session.headers.update({'X-CSRF-Token': self.csrf_token})

        payload = {
            "ShareType": 1,
            "RecipientEmailAddress": "",
            "SenderName": self.credentials['user'].split("@")[0],
            "SenderEmail": self.credentials['user'],
            "NotifyUserOnGuestTransfer": 1,
            "SenderCarbonCopy": 0,
            "EmailSubject": "MCS MFT",
            "EmailBody": "",
            "ExpirationTimestamp": expiry,
            "PasswordIsSet": 0 if not password else 1,
            "Password": '' if not password else password,
            "IncludePasswordInEmail": 0,
            "MaxFileSize": 0
        }

        response = self.session.post(urljoin(self.host, r"Web%20Client/Share/CreateFileShare.xml?Command=CreateFileShare"), data=payload)
        return {"url": re.findall(r"(?<=<ShareURL>)[\W\w]+(?=<\/ShareURL>)", response.text)[0],  # ShareURL Encoded
                "token": re.findall(r"(?<=<ShareToken>)[\W\w]+(?=<\/ShareToken>)", response.text)[0]}

    def _upload_files(self, files: [str], token: str):
        """Uploads the files to the previously created file share."""
        transfer_id = 1
        for file in files:
            self.session.post(urljoin(self.host, fr"Web%20Client/Share/MultipleFileUploadResult.htm?Command=UploadFileShare&TransferID={transfer_id}&File={file}&ShareToken={token}&IsVirtual=0&CsrfToken={self.csrf_token}"),
                              files={"file": open(file, 'rb')})
            transfer_id += 1

