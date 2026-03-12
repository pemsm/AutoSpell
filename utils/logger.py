import logging
import os
from datetime import datetime

def setup_logger():
    """Configura o sistema de logs para o AutoSpell."""
    
    # Cria a pasta de logs se ela não existir
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Nome do arquivo de log baseado na data atual
    log_filename = datetime.now().strftime("autospell_%Y-%m-%d.log")
    log_path = os.path.join(log_dir, log_filename)

    # Configuração do Logger Principal
    logger = logging.getLogger("AutoSpell")
    logger.setLevel(logging.DEBUG)

    # Formato das mensagens: [Data Hora] [Nível] Mensagem
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

    # Handler para o arquivo (Salva tudo: DEBUG, INFO, WARNING, ERROR)
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Handler para o console (Exibe apenas INFO e acima para não poluir)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Evita duplicidade de logs se o logger já estiver configurado
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Instância global para ser importada pelos outros módulos
logger = setup_logger()