from info import *
from pyrogram import Client
from subprocess import Popen

from pyrogram import utils

def get_peer_type_new(peer_id: int) -> str:
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"):
        return "user"
    elif peer_id_str.startswith("-100"):
        return "channel"
    else:
        return "chat"

utils.get_peer_type = get_peer_type_new

User = Client(name="user", session_string=SESSION)
DlBot = Client(name="auto-delete", 
               api_id=API_ID,
               api_hash=API_HASH,           
               bot_token=BOT_TOKEN)

class Bot(Client):   
    def __init__(self):
        super().__init__(   
           "bot",
            api_id=API_ID,
            api_hash=API_HASH,           
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"})
    async def start(self):                        
        await super().start()        
        await User.start()
        Popen("python3 -m utils.delete", shell=True)       
        print("Bot Started 👍🙂")   
    async def stop(self, *args):
        await super().stop()
