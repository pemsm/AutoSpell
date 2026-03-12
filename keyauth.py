import os
import json as jsond
import time
import platform
import subprocess
import logging
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
    # Não usamos exit aqui para evitar fechar o terminal do usuário sem ele ler
    raise SystemExit

class api:
    name = ownerid = version = hash_to_check = ""
    sessionid = enckey = ""
    initialized = False

    class user_data_class:
        username = ip = hwid = expires = subscription = ""

    user_data = user_data_class()

    def __init__(self, name, ownerid, version, hash_to_check):
        if len(ownerid) != 10:
            raise ValueError("OwnerID inválido. Deve ter 10 caracteres conforme o painel KeyAuth.")
        
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

        if response in ["KeyAuth_Invalid", "KeyAuth_Error", "KeyAuth_Timeout"]:
            print(f"❌ Erro crítico na inicialização do KeyAuth: {response}")
            self.initialized = False
            return

        try:
            json_data = jsond.loads(response)
        except jsond.JSONDecodeError:
            print("❌ Erro ao processar resposta do servidor (JSON Inválido).")
            return

        if json_data.get("message") == "invalidver":
            if json_data.get("download") != "":
                print(f"📢 Nova versão encontrada: {json_data['download']}")
                if platform.system() == 'Windows':
                    os.system(f"start {json_data['download']}")
            print("❌ Versão obsoleta. O programa será encerrado.")
            time.sleep(3)
            os._exit(1)

        if json_data.get("success"):
            self.sessionid = json_data["sessionid"]
            self.initialized = True
        else:
            print(f"❌ Falha no Init: {json_data.get('message')}")

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
            print("⚠️ API não inicializada. Tentando inicializar...")
            self.init()
            if not self.initialized:
                raise ConnectionError("Não foi possível conectar ao servidor de autenticação.")
        return True

    def __do_request(self, post_data):
        try:
            response = requests.post(
                "https://keyauth.win/api/1.3/", data=post_data, timeout=10
            )

            if response.status_code != 200:
                return "KeyAuth_Error"

            # Alguns tipos de resposta não assinam o cabeçalho
            if post_data["type"] in ["log", "file"]:
                return response.text

            signature = response.headers.get("x-signature-ed25519")
            timestamp = response.headers.get("x-signature-timestamp")

            if not signature or not timestamp:
                return "KeyAuth_Invalid"

            # Verificação de sincronia de tempo (Prevenção de Replay Attack)
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
                # Tenta pegar o SID do usuário logado como HWID único
                winuser = os.getlogin()
                sid, domain, type = win32security.LookupAccountName(None, winuser)
                return win32security.ConvertSidToStringSid(sid)
            elif platform.system() == 'Linux':
                if os.path.exists("/etc/machine-id"):
                    with open("/etc/machine-id") as f:
                        return f.read().strip()
            return "DEFAULT_HWID"
        except Exception:
            # Fallback para UUID se falhar no Windows
            import uuid
            return str(uuid.getnode())