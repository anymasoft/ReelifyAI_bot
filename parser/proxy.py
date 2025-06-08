import asyncio
from proxybroker import Broker
from typing import Optional

class ProxyManager:
    def __init__(self):
        self.broker = Broker(max_tries=3)
        self.proxies = asyncio.Queue()

    async def fetch_proxies(self):
        await self.broker.find(types=['HTTP', 'HTTPS'], limit=10)
        while True:
            proxy = await self.broker.get()
            if proxy is None:
                break
            await self.proxies.put(f"http://{proxy.host}:{proxy.port}")

    async def get_proxy(self) -> Optional[str]:
        if self.proxies.empty():
            await self.fetch_proxies()
        try:
            return self.proxies.get_nowait()
        except asyncio.QueueEmpty:
            return None