# Managed File Transfer (MFT)
An unofficial Python Web API wrapper for SolarWinds Serv-U Managed File Transfer.

## Installation :
`pip install git+https://github.com/GitPushPullLegs/mft.git`

## Quickstart:
**Sending Demo Code**

```python
from mft import Client
from datetime import datetime, timedelta

client = Client(host='https://host.com/')
client.login(username='username', password='password')
url_to_share = client.create_file_share(share_type=Client.ShareType.send,
                                        files=['/path/to/your/file.txt'],
                                        expiry=int((datetime.now() + timedelta(days=30)).timestamp()),  # Unix timestamp of when the file share should expire.
                                        password='file-login-password')  # The password needed to access the file share.

print(url_to_share)  # This is the url to the file share.
```

**Requesting Demo Code**

```python
from mft import Client

client = Client(host='https://host.com/')
client.login(username='username', password='password')
url_to_share = client.create_file_share(share_type=Client.ShareType.request,
                                        expiry=1686046380,  # Unix timestamp of when the file share should expire.
                                        password='file-login-password')  # The password needed to access the file share.

print(url_to_share)  # This is the url to the file share.
```