import json
import requests

from uuid import uuid4

class ClientJupyterKernel:
    def __init__(self, url, mount_dir):
        self.url = f"http://{url}/execute"
        
        self.mount_dir = mount_dir
        self.conv_id = uuid4().hex

    def execute(self, code):
        payload = {"convid": self.conv_id, "mount_dir": self.mount_dir, "code": code}
        response = requests.post(self.url, data=json.dumps(payload))
        response_data = response.json()
        return response_data["result"]

def extract_code(response):
    if response.find('```python') != -1:
        code = response[response.find('```python') + len('```python'):]
        code = code[:code.find('```')].lstrip('\n').rstrip('\n')
    else:
        code = response
    return code