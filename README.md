# Managed File Transfer (MFT)
A library to facilitate sharing files via SolarWinds Serv-U Managed File Transfer.

## Installation :
`pip install git+https://github.com/GitPushPullLegs/mft.git`

## Quickstart:
**Demo Code**

```python
from mft import Client

client = Client(host='https://host.com/')
client.login(username='your.login@yourdomain.com', password='password')
url_to_share = client.upload_files(files=['/path/to/your/file.txt'],
                                   expiry=int((datetime.now() + timedelta(days=30)).timestamp()),  # Timestamp of when the file should expire.
                                   password='file-login-password')  # The password needed to access the files.

print(url_to_share)  # This is the url to the files that you'll share.
```