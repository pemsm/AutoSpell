import os
import time
import pyautogui
import json
import numpy as np
import cv2
import logging
from PIL import ImageGrab

# Configurações de Tela
SCREEN_W = 1920
SCREEN_H = 1080
ROI_OFFSET_X = 960  

# Otimização extrema para evitar lag no rastro
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

logger = logging.getLogger(__name__)

def capturar_brilho():
    """Calcula a média de brilho apenas na ROI direita para maior performance."""
    try:
        # Captura apenas a metade direita da tela onde o jogo acontece
        img = np.array(ImageGrab.grab(bbox=(ROI_OFFSET_X, 0, SCREEN_W, SCREEN_H)))
        return np.mean(img)
    except:
        return 0

def identificar_padrao_na_tela():
    """Busca feitiço na tela usando Template Matching Robusto na ROI direita."""
    logging.info("Buscando padrão na ROI Direita...")
    
    try:
        # Captura apenas a metade direita
        print_completo = np.array(ImageGrab.grab(bbox=(ROI_OFFSET_X, 0, SCREEN_W, SCREEN_H)))
        print_bgr = cv2.cvtColor(print_completo, cv2.COLOR_RGB2BGR)
        print_gray = cv2.cvtColor(print_bgr, cv2.COLOR_BGR2GRAY)
    except Exception as e:
        logging.error(f"Erro na captura de tela: {e}")
        return None

    # Threshold binário para destacar o rastro
    _, print_thresh = cv2.threshold(print_gray, 150, 255, cv2.THRESH_BINARY)
    kernel = np.ones((3,3), np.uint8)
    print_thresh = cv2.morphologyEx(print_thresh, cv2.MORPH_OPEN, kernel)

    melhor_match = None
    maior_score = 0
    
    if not os.path.exists("padroes"):
        logging.warning("Pasta 'padroes' não encontrada.")
        return None
    
    padroes_arquivos = [f for f in os.listdir("padroes") if f.lower().endswith(('.png', '.jpg'))]

    for arq in padroes_arquivos:
        path_template = os.path.join("padroes", arq)
        template = cv2.imread(path_template, 0)
        if template is None: continue
            
        _, template_thresh = cv2.threshold(template, 150, 255, cv2.THRESH_BINARY)
        template_thresh = cv2.morphologyEx(template_thresh, cv2.MORPH_OPEN, kernel)
        
        h_print, w_print = print_thresh.shape[:2]
        h_temp, w_temp = template_thresh.shape[:2]

        if h_temp >= h_print or w_temp >= w_print:
            template_thresh = cv2.resize(template_thresh, (w_print - 10, h_print - 10))

        res = cv2.matchTemplate(print_thresh, template_thresh, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        if max_val > maior_score:
            maior_score = max_val
            if max_val > 0.40: 
                melhor_match = arq
                
    return melhor_match

def run_macro(comando, status_widget, stats_callback, tecla_console="f8"):
    try:
        logging.info(f"--- INICIANDO CICLO DE MACRO: {comando} ---")
        
        # 1. COMANDO DE CONSOLE
        status_widget.configure(text="Abrindo Console...", text_color="yellow")
        pyautogui.press(tecla_console)
        time.sleep(0.5)
        
        pyautogui.write(comando, interval=0.05)
        time.sleep(0.2)
        pyautogui.press('enter')
        time.sleep(0.3)
        
        # 2. FECHAR CONSOLE
        pyautogui.press(tecla_console) 
        time.sleep(0.8) 

        # 3. IDENTIFICAR PADRÃO
        status_widget.configure(text="Analisando Padrão...", text_color="cyan")
        nome_padrao = identificar_padrao_na_tela()
        
        if not nome_padrao:
            logging.warning("Padrão não identificado.")
            pyautogui.press('esc')
            time.sleep(3.0)
            return

        # 4. CARREGAR DADOS
        if not os.path.exists("coordenadas_calibradas.json"):
            pyautogui.press('esc')
            return

        with open("coordenadas_calibradas.json", "r") as f:
            all_data = json.load(f)
        
        config = all_data.get(nome_padrao)
        if not config or "points" not in config:
            pyautogui.press('esc')
            return

        points = config["points"]
        p0 = points[0]
        
        # 5. MOVIMENTO GRADUAL PARA O PONTO INICIAL (ANTES DO 'X')
        # Extrai coordenadas iniciais
        start_x = (p0[0] if isinstance(p0, list) else p0["x"]) + ROI_OFFSET_X
        start_y = p0[1] if isinstance(p0, list) else p0["y"]

        status_widget.configure(text="Posicionando Mouse...", text_color="white")
        # Move gradualmente para não contar como erro no minigame novo
        pyautogui.moveTo(start_x, start_y, duration=0.4) 
        time.sleep(0.1)

        # 6. INICIAR MINIGAME (Mouse já está no lugar certo!)
        status_widget.configure(text=f"Rodando {nome_padrao}", text_color="#FF8C00")
        pyautogui.press('x')
        time.sleep(1.1) # Aguarda o jogo processar a abertura

        # 7. EXECUTAR RASTRO + TECLAS (C, X, Z)
        pyautogui.mouseDown()
        
        for p in points[1:]:
            curr_x, curr_y = (p[0], p[1]) if isinstance(p, list) else (p["x"], p["y"])
            
            if isinstance(p, dict):
                wait_time = p.get("wait", 0.005)
                tecla_para_apertar = p.get("key", None)
            else:
                wait_time = 0.005
                tecla_para_apertar = None
                
            pyautogui.moveTo(curr_x + ROI_OFFSET_X, curr_y)
            
            if tecla_para_apertar:
                pyautogui.press(tecla_para_apertar)

            if wait_time > 0:
                time.sleep(wait_time)

        pyautogui.mouseUp()

        # 8. RESET E ESTATÍSTICAS
        status_widget.configure(text="Sucesso! Resetando (3s)...", text_color="green")
        pyautogui.mouseUp()
        time.sleep(3.0)
        
        if capturar_brilho() > 90:
            stats_callback('sucessos')
        else:
            stats_callback('fracassos')
            pyautogui.press('esc')

    except Exception as e:
        logging.exception("Erro crítico no vision_engine:")
        pyautogui.press('esc')
        status_widget.configure(text="Erro no Ciclo", text_color="red")
        time.sleep(3.0)