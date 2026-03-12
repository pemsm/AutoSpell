import os
import json as jsond
import time
import platform
import subprocess
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from discord_interactions import verify_key

# Configuração de log para ajudar no diagnóstico
logger = logging.getLogger(__name__)

try:
    if os.name == 'nt':
        import win32security
    import requests
except ModuleNotFoundError:
    print("Dependências faltando. Instalando módulos necessários...")
    os.system("pip install pywin32 requests discord-interactions qrcode pillow")
    print("Módulos instalados! Reinicie o script manualmente.")
    time.sleep(2)
    raise SystemExit

class api:
    name = ownerid = secret = version = hash_to_check = ""
    sessionid = enckey = ""
    initialized = False

    class user_data_class:
        username = ip = hwid = expires = subscription = ""

    user_data = user_data_class()

    def __init__(self, name, ownerid, secret, version, hash_to_check):
        if len(ownerid) != 10:
            raise ValueError("OwnerID inválido. Deve ter 10 caracteres conforme o painel KeyAuth.")
        
        self.name = name
        self.ownerid = ownerid
        self.secret = secret
        self.version = version
        self.hash_to_check = hash_to_check
        # O init() não é chamado aqui para evitar travar a Main Thread da UI

    def init(self):
        if self.sessionid != "":
            return
        
        # O campo 'init_set' é OBRIGATÓRIO na API 1.3 para enviar o Secret
        post_data = {
            "type": "init",
            "ver": self.version,
            "hash": self.hash_to_check,
            "name": self.name,
            "ownerid": self.ownerid,
            "init_set": self.secret 
        }

        response = self.__do_request(post_data)

        if response in ["KeyAuth_Invalid", "KeyAuth_Error", "KeyAuth_Timeout"]:
            print(f"❌ Erro de comunicação com o servidor: {response}")
            self.initialized = False
            return

        try:
            json_data = jsond.loads(response)
        except jsond.JSONDecodeError:
            print("❌ Erro ao processar resposta do servidor (JSON Inválido).")
            return

        if json_data.get("success"):
            self.sessionid = json_data["sessionid"]
            self.enckey = json_data.get("enckey", "")
            self.initialized = True
        elif json_data.get("message") == "invalidver":
            if json_data.get("download") != "":
                print(f"📢 Nova versão encontrada: {json_data['download']}")
                if platform.system() == 'Windows':
                    os.system(f"start {json_data['download']}")
            print("❌ Versão obsoleta. O programa será encerrado.")
            time.sleep(3)
            os._exit(1)
        else:
            # Aqui aparecerá o motivo real se o Token ainda falhar
            print(f"❌ Falha no Init: {json_data.get('message')}")
            self.initialized = False

    def register(self, user, password, license_key, hwid=None):
        self.checkinit()
        hwid = hwid or others.get_hwid()

        post_data = {
            "type": "register",
            "username": user,
            "pass": password,
            "key": license_key,
            "hwid": hwid,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        return self.__process_auth_response(self.__do_request(post_data))

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
        
        return self.__process_auth_response(self.__do_request(post_data))

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
        
        return self.__process_auth_response(self.__do_request(post_data))

    def checkinit(self):
        if not self.initialized:
            self.init()
            if not self.initialized:
                raise ConnectionError("Não foi possível conectar ao servidor de autenticação.")
        return True

    def __do_request(self, post_data):
        try:
            # Adicionado headers básicos para garantir que o servidor aceite o POST
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            response = requests.post(
                "https://keyauth.win/api/1.3/", data=post_data, headers=headers, timeout=10
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
            if abs((datetime.now(timezone.utc) - server_time).total_seconds()) > 60:
                return "KeyAuth_Timeout"

            pub_key = '5586b4bc69c7a4b487e4563a4cd96afd39140f919bd31cea7d1c6a1e8439422b'
            if not verify_key(response.text.encode(), signature, timestamp, pub_key):
                return "KeyAuth_Invalid_Signature"

            return response.text
        except Exception as e:
            logger.error(f"Erro na requisição KeyAuth: {e}")
            return "KeyAuth_Error"

    def __process_auth_response(self, response):
        try:
            json_data = jsond.loads(response)
            if json_data["success"]:
                self.__load_user_data(json_data["info"])
                return True, json_data["message"]
            return False, json_data["message"]
        except:
            return False, "Erro na resposta do servidor."

    def __load_user_data(self, data):
        self.user_data.username = data.get("username", "N/A")
        self.user_data.ip = data.get("ip", "N/A")
        self.user_data.hwid = data.get("hwid") or "N/A"
        
        subs = data.get("subscriptions", [])
        if subs:
            self.user_data.expires = subs[0].get("expiry", "N/A")
            self.user_data.subscription = subs[0].get("subscription", "N/A")

class others:
    @staticmethod
    def get_hwid():
        try:
            if platform.system() == 'Windows':
                import win32security
                winuser = os.getlogin()
                sid, domain, type = win32security.LookupAccountName(None, winuser)
                return win32security.ConvertSidToStringSid(sid)
            elif platform.system() == 'Linux':
                if os.path.exists("/etc/machine-id"):
                    with open("/etc/machine-id") as f:
                        return f.read().strip()
            return "DEFAULT_HWID"
        except Exception:
            import uuid
            return str(uuid.getnode())

    @staticmethod
    def get_self_hash():
        sha256_hash = hashlib.sha256()
        with open(os.path.abspath(__file__), "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

# --- INSTANCIAÇÃO DA API ---
keyauthapp = api(
    name = "Wizard HUD - Ghost Edition",
    ownerid = "TqGr3LrSGL",
    secret = "144abb63da41c5424a5c54eb5f86a4ec31e7c7191f56292056c93fcd73b8c395",
    version = "1.1.0",
    hash_to_check = "" 
)