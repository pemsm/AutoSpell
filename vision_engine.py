import os
import time
import pyautogui
import json
import numpy as np
import cv2
import logging
from PIL import ImageGrab

# --- CONFIGURAÇÕES DE TELA ---
SCREEN_W = 1920
SCREEN_H = 1080
ROI_OFFSET_X = 960  

# Otimização para evitar lag
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

logger = logging.getLogger(__name__)

def capturar_brilho():
    """Calcula a média de brilho na ROI direita para validar sucesso."""
    try:
        img = np.array(ImageGrab.grab(bbox=(ROI_OFFSET_X, 0, SCREEN_W, SCREEN_H)))
        return np.mean(img)
    except Exception as e:
        logging.error(f"Erro ao capturar brilho: {e}")
        return 0

def identificar_padrao_na_tela():
    """Busca feitiço na tela usando Template Matching na ROI direita."""
    try:
        # Captura apenas a metade direita (onde o minigame aparece)
        print_completo = np.array(ImageGrab.grab(bbox=(ROI_OFFSET_X, 0, SCREEN_W, SCREEN_H)))
        print_bgr = cv2.cvtColor(print_completo, cv2.COLOR_RGB2BGR)
        print_gray = cv2.cvtColor(print_bgr, cv2.COLOR_BGR2GRAY)
        
        # Processamento para destacar o rastro
        _, print_thresh = cv2.threshold(print_gray, 150, 255, cv2.THRESH_BINARY)
        kernel = np.ones((3,3), np.uint8)
        print_thresh = cv2.morphologyEx(print_thresh, cv2.MORPH_OPEN, kernel)

        melhor_match = None
        maior_score = 0
        
        if not os.path.exists("padroes"): return None
        padroes_arquivos = [f for f in os.listdir("padroes") if f.lower().endswith(('.png', '.jpg'))]

        for arq in padroes_arquivos:
            template = cv2.imread(os.path.join("padroes", arq), 0)
            if template is None: continue
            
            _, template_thresh = cv2.threshold(template, 150, 255, cv2.THRESH_BINARY)
            template_thresh = cv2.morphologyEx(template_thresh, cv2.MORPH_OPEN, kernel)
            
            h_p, w_p = print_thresh.shape[:2]
            h_t, w_t = template_thresh.shape[:2]
            
            # Redimensiona template se for maior que a tela capturada
            if h_t >= h_p or w_t >= w_p:
                template_thresh = cv2.resize(template_thresh, (w_p - 10, h_p - 10))

            res = cv2.matchTemplate(print_thresh, template_thresh, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            
            if max_val > maior_score:
                maior_score = max_val
                if max_val > 0.40: # Threshold de confiança
                    melhor_match = arq
                    
        return melhor_match
    except Exception as e:
        logging.error(f"Erro na identificação: {e}")
        return None

def run_macro(comando, status_widget, stats_callback, get_running_status, tecla_console="f8", skip_list=[]):
    """
    Executa o macro restaurando a ordem funcional com suporte a Skip List.
    """
    try:
        # --- PASSO 0: CHECKPOINT INICIAL ---
        if not get_running_status(): return

        # --- PASSO 1: ABRIR CONSOLE E INVOCAR ---
        status_widget.configure(text="Abrindo Console...", text_color="yellow")
        pyautogui.press(tecla_console)
        time.sleep(0.5)
        
        pyautogui.write(comando, interval=0.05)
        time.sleep(0.2)
        pyautogui.press('enter')
        time.sleep(0.3)
        
        # Fecha console para permitir a visão do padrão
        pyautogui.press(tecla_console) 
        time.sleep(0.8) 

        # --- PASSO 2: IDENTIFICAR PADRÃO ---
        status_widget.configure(text="Analisando Padrão...", text_color="cyan")
        nome_padrao = identificar_padrao_na_tela()

        # --- PASSO 3: LÓGICA DE SKIP (Identificou, mas está na lista negra) ---
        if nome_padrao and nome_padrao in skip_list:
            status_widget.configure(text=f"SKIP: {nome_padrao}", text_color="#f39c12")
            pyautogui.press('esc')
            # Aguarda um pouco antes de permitir o próximo ciclo
            for _ in range(15): 
                if not get_running_status(): return
                time.sleep(0.1)
            return

        if not nome_padrao:
            logging.warning("Padrão não identificado.")
            pyautogui.press('esc')
            time.sleep(2.0)
            return

        # --- PASSO 4: CARREGAR COORDENADAS ---
        if not os.path.exists("coordenadas_calibradas.json"): return
        with open("coordenadas_calibradas.json", "r") as f:
            all_data = json.load(f)
        
        config = all_data.get(nome_padrao)
        if not config or "points" not in config:
            pyautogui.press('esc')
            return

        points = config["points"]
        p0 = points[0]
        
        # Coordenadas do ponto inicial
        start_x = (p0[0] if isinstance(p0, list) else p0["x"]) + ROI_OFFSET_X
        start_y = p0[1] if isinstance(p0, list) else p0["y"]

        # --- PASSO 5: POSICIONAMENTO ---
        status_widget.configure(text="Posicionando Mouse...", text_color="white")
        pyautogui.moveTo(start_x, start_y, duration=0.4) 
        time.sleep(0.1)
        
        if not get_running_status(): return

        # --- PASSO 6: INICIAR MINIGAME E RASTRO ---
        status_widget.configure(text=f"Executando {nome_padrao}", text_color="#FF8C00")
        pyautogui.press('x')
        time.sleep(1.1) 
        
        pyautogui.mouseDown()
        for p in points[1:]:
            if not get_running_status():
                pyautogui.mouseUp()
                return
                
            curr_x, curr_y = (p[0], p[1]) if isinstance(p, list) else (p["x"], p["y"])
            pyautogui.moveTo(curr_x + ROI_OFFSET_X, curr_y)
            
            # Pressiona teclas (C, X, Z) se gravadas no ponto
            if isinstance(p, dict) and p.get("key"):
                pyautogui.press(p["key"])

            wait_time = p.get("wait", 0.005) if isinstance(p, dict) else 0.005
            time.sleep(max(0, wait_time))

        pyautogui.mouseUp()

        # --- PASSO 7: FINALIZAÇÃO E VALIDAÇÃO ---
        status_widget.configure(text="Sucesso! Resetando...", text_color="green")
        
        # Espera o minigame fechar e o brilho estabilizar
        for _ in range(30): 
            if not get_running_status(): return
            time.sleep(0.1)
        
        if capturar_brilho() > 90:
            stats_callback('sucessos')
        else:
            stats_callback('fracassos')
            pyautogui.press('esc')

    except Exception as e:
        logging.exception("Erro crítico no vision_engine:")
        pyautogui.press('esc')
        status_widget.configure(text="Erro no Ciclo", text_color="red")
        time.sleep(2.0)