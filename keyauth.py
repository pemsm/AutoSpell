import os
import json as jsond
import time
import platform
import subprocess
from datetime import datetime, timezone, timedelta
from discord_interactions import verify_key

try:
    if os.name == 'nt':
        import win32security
    import requests
except ModuleNotFoundError:
    print("Dependências faltando. Instalando módulos necessários...")
    os.system("pip install pywin32 requests discord-interactions qrcode pillow")
    print("Módulos instalados! Reinicie o script.")
    time.sleep(1.5)
    os._exit(1)

class api:
    name = ownerid = version = hash_to_check = ""
    sessionid = enckey = ""
    initialized = False

    class user_data_class:
        username = ip = hwid = expires = subscription = ""

    user_data = user_data_class()

    def __init__(self, name, ownerid, version, hash_to_check):
        if len(ownerid) != 10:
            print("OwnerID inválido. Verifique no painel do KeyAuth.")
            time.sleep(3)
            os._exit(1)
        
        self.name = name
        self.ownerid = ownerid
        self.version = version
        self.hash_to_check = hash_to_check
        self.init()

    def init(self):
        if self.sessionid != "":
            return
        
        post_data = {
            "type": "init",
            "ver": self.version,
            "hash": self.hash_to_check,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        if response in ["KeyAuth_Invalid", "KeyAuth_Error"]:
            print(f"Erro na Inicialização: {response}")
            return

        json_data = jsond.loads(response)

        if json_data.get("message") == "invalidver":
            if json_data.get("download") != "":
                print("Nova versão encontrada. Baixando...")
                os.system(f"start {json_data['download']}")
            os._exit(1)

        if json_data.get("success"):
            self.sessionid = json_data["sessionid"]
            self.initialized = True

    def register(self, user, password, license, hwid=None):
        """Método de registro que estava faltando no seu código anterior"""
        self.checkinit()
        hwid = hwid or others.get_hwid()

        post_data = {
            "type": "register",
            "username": user,
            "pass": password,
            "key": license,
            "hwid": hwid,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)
        json_data = jsond.loads(response)

        if json_data["success"]:
            self.__load_user_data(json_data["info"])
            return True, json_data["message"]
        return False, json_data["message"]

    def login(self, user, password, hwid=None):
        self.checkinit()
        hwid = hwid or others.get_hwid()

        post_data = {
            "type": "login",
            "username": user,
            "pass": password,
            "hwid": hwid,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }
        
        response = self.__do_request(post_data)
        json_data = jsond.loads(response)

        if json_data["success"]:
            self.__load_user_data(json_data["info"])
            return True, json_data["message"]
        return False, json_data["message"]

    def license(self, key, hwid=None):
        self.checkinit()
        hwid = hwid or others.get_hwid()

        post_data = {
            "type": "license",
            "key": key,
            "hwid": hwid,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }
        
        response = self.__do_request(post_data)
        json_data = jsond.loads(response)

        if json_data["success"]:
            self.__load_user_data(json_data["info"])
            return True, json_data["message"]
        return False, json_data["message"]

    def checkinit(self):
        if not self.initialized:
            print("API não inicializada. Chame o método init() primeiro.")
            os._exit(1)
        return True

    def __do_request(self, post_data):
        try:
            response = requests.post(
                "https://keyauth.win/api/1.3/", data=post_data, timeout=10
            )

            if response.status_code != 200:
                return "KeyAuth_Error"

            if post_data["type"] in ["log", "file"]:
                return response.text

            signature = response.headers.get("x-signature-ed25519")
            timestamp = response.headers.get("x-signature-timestamp")

            if not signature or not timestamp:
                return "KeyAuth_Invalid"

            server_time = datetime.fromtimestamp(int(timestamp), timezone.utc)
            if (datetime.now(timezone.utc) - server_time) > timedelta(seconds=30):
                return "KeyAuth_Timeout"

            pub_key = '5586b4bc69c7a4b487e4563a4cd96afd39140f919bd31cea7d1c6a1e8439422b'
            if not verify_key(response.text.encode(), signature, timestamp, pub_key):
                return "KeyAuth_Invalid_Signature"

            return response.text
        except Exception:
            return "KeyAuth_Error"

    def __load_user_data(self, data):
        self.user_data.username = data["username"]
        self.user_data.ip = data["ip"]
        self.user_data.hwid = data["hwid"] or "N/A"
        # Garante que acessamos a lista de inscrições com segurança
        if data.get("subscriptions"):
            self.user_data.expires = data["subscriptions"][0]["expiry"]
            self.user_data.subscription = data["subscriptions"][0]["subscription"]

class others:
    @staticmethod
    def get_hwid():
        try:
            if platform.system() == 'Windows':
                import win32security
                winuser = os.getlogin()
                sid = win32security.LookupAccountName(None, winuser)[0]
                return win32security.ConvertSidToStringSid(sid)
            elif platform.system() == 'Linux':
                with open("/etc/machine-id") as f:
                    return f.read().strip()
            else:
                return "NON_WINDOWS_HWID"
        except:
            return "UNKNOWN_HWID"