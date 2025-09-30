import os
import re
import time
import json
import docker
import asyncio
import tornado
import logging

from tornado.escape import json_encode, json_decode, url_escape
from tornado.websocket import websocket_connect, WebSocketHandler
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from uuid import uuid4

logging.basicConfig(level=logging.INFO)

def strip_ansi(o: str) -> str:
    """
    Removes ANSI escape sequences from `o`, as defined by ECMA-048 in
    http://www.ecma-international.org/publications/files/ECMA-ST/Ecma-048.pdf

    # https://github.com/ewen-lbh/python-strip-ansi/blob/master/strip_ansi/__init__.py
    
    >>> strip_ansi("\\033[33mLorem ipsum\\033[0m")
    'Lorem ipsum'
    
    >>> strip_ansi("Lorem \\033[38;25mIpsum\\033[0m sit\\namet.")
    'Lorem Ipsum sit\\namet.'
    
    >>> strip_ansi("")
    ''
    
    >>> strip_ansi("\\x1b[0m")
    ''
    
    >>> strip_ansi("Lorem")
    'Lorem'
    
    >>> strip_ansi('\\x1b[38;5;32mLorem ipsum\\x1b[0m')
    'Lorem ipsum'
    
    >>> strip_ansi('\\x1b[1m\\x1b[46m\\x1b[31mLorem dolor sit ipsum\\x1b[0m')
    'Lorem dolor sit ipsum'
    """
    
    # pattern = re.compile(r'/(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]/')
    pattern = re.compile(r'\x1B\[\d+(;\d+){0,2}m')
    stripped = pattern.sub('', o)
    return stripped

class JupyterKernel:
    def __init__(
        self,
        url_suffix,
        convid,
        lang="python"
    ):
        self.base_url = f"http://{url_suffix}"
        self.base_ws_url = f"ws://{url_suffix}"
        self.lang = lang
        self.kernel_id = None
        self.ws = None
        self.convid = convid
        logging.info(f"Jupyter kernel created for conversation {convid} at {url_suffix}")

        self.heartbeat_interval = 10000  # 10 seconds
        self.heartbeat_callback = None

    async def initialize(self):
        await self.execute(r"%colors nocolor")
        # pre-defined tools
        self.tools_to_run = [
            # TODO: You can add code for your pre-defined tools here
        ]
        for tool in self.tools_to_run:
            # logging.info(f"Tool initialized:\n{tool}")
            await self.execute(tool)
    
    async def _send_heartbeat(self):
        if not self.ws:
            return
        try:
            self.ws.ping()
            # logging.info("Heartbeat sent...")
        except tornado.iostream.StreamClosedError:
            # logging.info("Heartbeat failed, reconnecting...")
            try:
                await self._connect()
            except ConnectionRefusedError:
                logging.info("ConnectionRefusedError: Failed to reconnect to kernel websocket - Is the kernel still running?")

    async def _connect(self):
        if self.ws:
            self.ws.close()
            self.ws = None

        client = AsyncHTTPClient()
        if not self.kernel_id:
            n_tries = 5
            while n_tries > 0:
                try:
                    response = await client.fetch(
                        "{}/api/kernels".format(self.base_url),
                        method="POST",
                        body=json_encode({"name": self.lang}),
                    )
                    kernel = json_decode(response.body)
                    self.kernel_id = kernel["id"]
                    break
                except Exception as e:
                    # kernels are not ready yet
                    n_tries -= 1
                    await asyncio.sleep(1)
            
            if n_tries == 0:
                raise ConnectionRefusedError("Failed to connect to kernel")

        ws_req = HTTPRequest(
            url="{}/api/kernels/{}/channels".format(
                self.base_ws_url, url_escape(self.kernel_id)
            )
        )
        self.ws = await websocket_connect(ws_req)
        logging.info("Connected to kernel websocket")

        # Setup heartbeat
        if self.heartbeat_callback:
            self.heartbeat_callback.stop()
        self.heartbeat_callback = PeriodicCallback(self._send_heartbeat, self.heartbeat_interval)
        self.heartbeat_callback.start()

    async def execute(self, code, timeout=60):
        if not self.ws:
            await self._connect()

        msg_id = uuid4().hex
        self.ws.write_message(
            json_encode(
                {
                    "header": {
                        "username": "",
                        "version": "5.0",
                        "session": "",
                        "msg_id": msg_id,
                        "msg_type": "execute_request",
                    },
                    "parent_header": {},
                    "channel": "shell",
                    "content": {
                        "code": code,
                        "silent": False,
                        "store_history": False,
                        "user_expressions": {},
                        "allow_stdin": False,
                    },
                    "metadata": {},
                    "buffers": {},
                }
            )
        )

        outputs = []


        async def wait_for_messages():
            execution_done = False
            while not execution_done:
                msg = await self.ws.read_message()
                msg = json_decode(msg)
                msg_type = msg['msg_type']
                parent_msg_id = msg['parent_header'].get('msg_id', None)

                if parent_msg_id != msg_id:
                    continue

                if os.environ.get("DEBUG", False):
                    logging.info(f"MSG TYPE: {msg_type.upper()} DONE:{execution_done}\nCONTENT: {msg['content']}")

                if msg_type == 'error':
                    traceback = "\n\n\n\n".join(msg["content"]["traceback"])
                    outputs.append(traceback)
                    execution_done = True
                elif msg_type == 'stream':
                    outputs.append(msg['content']['text'])
                elif msg_type in ['execute_result', 'display_data']:
                    outputs.append(msg['content']['data']['text/plain'])
                    if 'image/png' in msg['content']['data']:
                        # use markdone to display image (in case of large image)
                        # outputs.append(f"\n<img src=\"data:image/png;base64,{msg['content']['data']['image/png']}\"/>\n")
                        # outputs.append(f"![image](data:image/png;base64,{msg['content']['data']['image/png']})")
                        outputs.append(f"[image]")

                elif msg_type == 'execute_reply':
                    execution_done = True
            return execution_done

        async def interrupt_kernel():
            client = AsyncHTTPClient()
            interrupt_response = await client.fetch(
                f"{self.base_url}/api/kernels/{self.kernel_id}/interrupt",
                method="POST",
                body=json_encode({"kernel_id": self.kernel_id}),
            )
            logging.info(f"Kernel interrupted: {interrupt_response}")

        try:
            execution_done = await asyncio.wait_for(wait_for_messages(), timeout)
        except asyncio.TimeoutError:
            await interrupt_kernel()
            return f"[Execution timed out ({timeout} seconds).]"

        if not outputs and execution_done:
            ret = "[Code executed successfully with no output]"
        else:
            ret = ''.join(outputs)

        # Remove ANSI
        ret = strip_ansi(ret) 

        if os.environ.get("DEBUG", False):
            logging.info(f"OUTPUT:\n{ret}")
        return ret

    async def shutdown_async(self):
        if self.kernel_id:
            client = AsyncHTTPClient()
            await client.fetch(
                "{}/api/kernels/{}".format(self.base_url, self.kernel_id),
                method="DELETE",
            )
            self.kernel_id = None
            if self.ws:
                self.ws.close()
                self.ws = None

class JupyterGatewayDocker:
    DOCKER_IMAGE = "docker.io/xingyaoww/codeact-executor"

    RESOURCE_CONSTRAINTS = {
        'mem_limit': '1g',
        'nano_cpus': int(1e9)
    }

    def __init__(self, name: str, mount_dir: dict):
        self.name = name
        self.mount_dir = mount_dir
        self.client = docker.from_env()
        self.container = None
        self.url = None

    def _get_free_port(self):
        """Get a free port from the OS."""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    def _wait_for_container(self, container):
        # Wait for a specific log message or condition indicating the app inside is ready
        # Note: This is just an example, you should adjust the condition to match your use case
        timeout = 60  # seconds
        start_time = time.time()
        while True:
            # Get the latest logs
            logs = container.logs().decode('utf-8')
            logging.info(logs)
            # Check for a specific message or condition in the logs
            if "Jupyter Kernel Gateway" in logs and "is available at" in logs:
                break
            # Exit if timeout reached
            if time.time() - start_time > timeout:
                logging.info("Timeout reached while waiting for container to be ready.")
                break
            time.sleep(1)

    def __enter__(self):
        # Check if the image exists locally, if not, pull it
        try:
            self.client.images.get(self.DOCKER_IMAGE)
        except docker.errors.ImageNotFound:
            self.client.images.pull(self.DOCKER_IMAGE)

        port = self._get_free_port()
        # Run the container and expose the port
        self.container = self.client.containers.run(
            self.DOCKER_IMAGE,
            name=self.name,
            detach=True,
            ports={"8888/tcp": port},
            volumes={
                k: {'bind': v, 'mode': 'rw'} 
                for k, v in self.mount_dir.items()
            },
            remove=True,  # Removes container when it's stopped
            **self.RESOURCE_CONSTRAINTS,
        )
        self._wait_for_container(self.container)

        url_suffix = f"localhost:{port}"
        return url_suffix

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.container:
            self.container.stop()
