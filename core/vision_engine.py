import os
import time
import pyautogui
import json
import numpy as np
import cv2
import logging
from mss import mss 

# --- CONFIGURAÇÕES DE TELA ---
SCREEN_W = 1920
SCREEN_H = 1080
ROI_OFFSET_X = 960  

# Otimização de latência do PyAutoGUI
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

logger = logging.getLogger(__name__)

def validar_sucesso_com_threshold(settings):
    """
    Detecta o balão de XP usando Threshold para ignorar o fundo transparente.
    Baseado nas configurações do settings.json.
    """
    try:
        conf = settings.get("detection", {})
        roi = conf.get("success_roi", {"x": 1540, "y": 490, "w": 360, "h": 80})
        thresh_val = conf.get("threshold_value", 210)
        min_pixels = conf.get("min_white_pixels", 400)

        with mss() as sct:
            # O mss usa coordenadas absolutas da tela
            monitor = {"top": roi["y"], "left": roi["x"], "width": roi["w"], "height": roi["h"]}
            sct_img = sct.grab(monitor)
            img = np.array(sct_img)
            
            # Converte para escala de cinza
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            
            # Aplica o Threshold: Mantém apenas o que for muito claro (texto/ícone)
            _, mask = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
            
            # Conta pixels brancos resultantes
            pixels_brancos = cv2.countNonZero(mask)
            
            # Se quiser debugar, descomente a linha abaixo para ver a contagem no log
            # logger.info(f"Pixels brancos detectados: {pixels_brancos}")
            
            return pixels_brancos > min_pixels
    except Exception as e:
        logger.error(f"Erro na validação por threshold: {e}")
        return False

def identificar_padrao_na_tela():
    """Busca feitiço usando Template Matching com detecção de bordas."""
    try:
        pasta_padroes = os.path.abspath("padroes")
        if not os.path.exists(pasta_padroes):
            logger.error(f"Pasta de padrões não encontrada: {pasta_padroes}")
            return None

        with mss() as sct:
            monitor = {"top": 0, "left": ROI_OFFSET_X, "width": SCREEN_W - ROI_OFFSET_X, "height": SCREEN_H}
            sct_img = sct.grab(monitor)
            print_completo = np.array(sct_img)
            
        print_bgr = cv2.cvtColor(print_completo, cv2.COLOR_BGRA2BGR)
        print_gray = cv2.cvtColor(print_bgr, cv2.COLOR_BGR2GRAY)
        
        print_edges = cv2.Canny(print_gray, 50, 150)
        kernel = np.ones((3,3), np.uint8)
        print_processed = cv2.dilate(print_edges, kernel, iterations=1)

        melhor_match = None
        maior_score = 0
        padroes_arquivos = [f for f in os.listdir(pasta_padroes) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        for arq in padroes_arquivos:
            path_template = os.path.join(pasta_padroes, arq)
            template = cv2.imread(path_template, 0)
            if template is None: continue
            
            template_edges = cv2.Canny(template, 50, 150)
            template_processed = cv2.dilate(template_edges, kernel, iterations=1)
            
            h_p, w_p = print_processed.shape[:2]
            h_t, w_t = template_processed.shape[:2]
            
            if h_t >= h_p or w_t >= w_p:
                nova_w = min(w_t, w_p - 1)
                nova_h = min(h_t, h_p - 1)
                template_processed = cv2.resize(template_processed, (nova_w, nova_h))

            res = cv2.matchTemplate(print_processed, template_processed, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            
            if max_val > maior_score:
                maior_score = max_val
                if max_val > 0.45:
                    melhor_match = arq
                    
        return melhor_match
    except Exception as e:
        logger.error(f"Erro na identificação: {e}")
        return None

def run_macro(comando, status_widget, stats_callback, get_running_status, tecla_console="f8", skip_list=[], settings={}):
    """Executa o ciclo completo do macro de visão."""
    try:
        if not get_running_status(): return

        # --- PASSO 1: INVOCAR COMANDO ---
        status_widget.configure(text=f"Invocando: {comando}", text_color="yellow")
        pyautogui.press(tecla_console)
        time.sleep(0.15)
        
        pyautogui.write(comando, interval=0.01)
        time.sleep(0.05)
        pyautogui.press('enter')
        time.sleep(0.1)
        pyautogui.press(tecla_console) 
        time.sleep(0.8) 

        # --- PASSO 2: IDENTIFICAR PADRÃO ---
        status_widget.configure(text="Escaneando Tela...", text_color="cyan")
        nome_padrao = identificar_padrao_na_tela()

        if not nome_padrao:
            status_widget.configure(text="Padrão não encontrado", text_color="red")
            time.sleep(0.2)
            pyautogui.press('esc')
            return

        if nome_padrao in skip_list:
            status_widget.configure(text=f"SKIP: {nome_padrao}", text_color="#f39c12")
            pyautogui.press('esc')
            return

        # --- PASSO 3: CARREGAR DADOS DE COORDENADAS ---
        json_path = os.path.abspath(os.path.join("data", "coordenadas_calibradas.json"))
        if not os.path.exists(json_path):
            status_widget.configure(text="Erro: JSON ausente", text_color="red")
            pyautogui.press('esc')
            return
            
        with open(json_path, "r", encoding='utf-8') as f:
            all_data = json.load(f)
        
        config = all_data.get(nome_padrao)
        if not config or "points" not in config:
            pyautogui.press('esc')
            return

        points = config["points"]
        if not points: return

        def get_xy(p):
            px = (p[0] if isinstance(p, list) else p["x"]) + ROI_OFFSET_X
            py = p[1] if isinstance(p, list) else p["y"]
            return px, py

        # --- PASSO 4: EXECUÇÃO DO RASTRO ---
        status_widget.configure(text=f"Executando: {nome_padrao}", text_color="#FF8C00")
        
        sx, sy = get_xy(points[0])
        pyautogui.moveTo(sx, sy, duration=0.12) 
        
        if not get_running_status(): return

        pyautogui.press('x') 
        time.sleep(0.6) 
        
        pyautogui.mouseDown()
        for p in points[1:]:
            if not get_running_status(): break
            curr_x, curr_y = get_xy(p)
            pyautogui.moveTo(curr_x, curr_y)
            if isinstance(p, dict) and p.get("key"):
                pyautogui.press(p["key"])
            wait_time = p.get("wait", 0.005) if isinstance(p, dict) else 0.005
            if wait_time > 0: time.sleep(wait_time)

        pyautogui.mouseUp()

        # --- PASSO 5: VALIDAÇÃO DINÂMICA (THRESHOLD) ---
        status_widget.configure(text="Validando...", text_color="green")
        
        sucesso_detectado = False
        # Busca o timeout do settings ou usa 5.0 como padrão
        limit_time = settings.get("detection", {}).get("detection_timeout", 5.0)
        timeout = time.time() + limit_time 

        while time.time() < timeout:
            if not get_running_status(): return
            
            # Usando a nova lógica de Threshold contra transparência
            if validar_sucesso_com_threshold(settings): 
                sucesso_detectado = True
                break
            time.sleep(0.1) # Intervalo entre scans para poupar CPU

        if sucesso_detectado:
            stats_callback('sucessos')
            status_widget.configure(text="✅ SUCESSO!", text_color="#2ecc71")
        else:
            stats_callback('fracassos')
            status_widget.configure(text="❌ FRACASSO", text_color="#e74c3c")
            pyautogui.press('esc')

    except Exception as e:
        logger.exception("Erro no vision_engine:")
        pyautogui.press('esc')
        status_widget.configure(text="Erro Crítico", text_color="red")