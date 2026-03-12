import json
import os
import hashlib
import sys
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- LÓGICA DE DIRETÓRIO BASE ---
# Detecta a pasta raiz do projeto (AutoSpell/) independente de onde o script é chamado
if getattr(sys, 'frozen', False):
    # Se estiver rodando como executável (.exe)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Se estiver rodando como script (.py), sobe um nível a partir de utils/
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")

def get_checksum():
    """Gera um hash MD5 do executável ou script principal."""
    md5_hash = hashlib.md5()
    path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.modules['__main__'].__file__)
    try:
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                md5_hash.update(byte_block)
        return md5_hash.hexdigest()
    except Exception as e:
        logger.error(f"Erro no Checksum: {e}")
        return ""

def load_json(filename, default=None):
    """Carrega dados da pasta 'data/' com tratamento de erros."""
    # Se o filename já for um caminho completo, usa ele. Se não, busca na pasta 'data'
    if not os.path.isabs(filename):
        abs_path = os.path.join(DATA_DIR, filename)
    else:
        abs_path = filename
    
    if os.path.exists(abs_path):
        try:
            with open(abs_path, "r", encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao ler JSON em {abs_path}: {e}")
            return default if default is not None else {}
    
    logger.warning(f"Arquivo não encontrado: {abs_path}")
    return default if default is not None else {}

def save_json(filename, data):
    """Salva dados em JSON dentro da pasta 'data/'."""
    try:
        if not os.path.isabs(filename):
            abs_path = os.path.join(DATA_DIR, filename)
        else:
            abs_path = filename

        # Garante que a pasta 'data' (ou qualquer outra necessária) exista
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
        with open(abs_path, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Dados salvos com sucesso em: {abs_path}")
    except Exception as e:
        logger.error(f"Erro ao salvar JSON: {e}")