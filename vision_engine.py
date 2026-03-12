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

# Otimização para evitar lag e interrupções bruscas
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

logger = logging.getLogger(__name__)

def capturar_brilho():
    """Calcula a média de brilho na ROI direita para validar sucesso."""
    try:
        with mss() as sct:
            monitor = {"top": 0, "left": ROI_OFFSET_X, "width": SCREEN_W - ROI_OFFSET_X, "height": SCREEN_H}
            img = np.array(sct.grab(monitor))
            # Converte para escala de cinza para um cálculo de brilho mais preciso
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            return np.mean(gray)
    except Exception as e:
        logging.error(f"Erro ao capturar brilho: {e}")
        return 0

def identificar_padrao_na_tela():
    """Busca feitiço usando Template Matching com detecção de bordas."""
    try:
        with mss() as sct:
            monitor = {"top": 0, "left": ROI_OFFSET_X, "width": SCREEN_W - ROI_OFFSET_X, "height": SCREEN_H}
            sct_img = sct.grab(monitor)
            print_completo = np.array(sct_img)
            
        print_bgr = cv2.cvtColor(print_completo, cv2.COLOR_BGRA2BGR)
        print_gray = cv2.cvtColor(print_bgr, cv2.COLOR_BGR2GRAY)
        
        # Canny para destacar o rastro
        print_edges = cv2.Canny(print_gray, 50, 150)
        kernel = np.ones((3,3), np.uint8)
        print_processed = cv2.dilate(print_edges, kernel, iterations=1)

        melhor_match = None
        maior_score = 0
        
        if not os.path.exists("padroes"): 
            return None
            
        padroes_arquivos = [f for f in os.listdir("padroes") if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        for arq in padroes_arquivos:
            template = cv2.imread(os.path.join("padroes", arq), 0)
            if template is None: continue
            
            # Processamento idêntico no template
            template_edges = cv2.Canny(template, 50, 150)
            template_processed = cv2.dilate(template_edges, kernel, iterations=1)
            
            h_p, w_p = print_processed.shape[:2]
            h_t, w_t = template_processed.shape[:2]
            
            # Garantir que o template é menor que a área capturada
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
        logging.error(f"Erro na identificação: {e}")
        return None

def run_macro(comando, status_widget, stats_callback, get_running_status, tecla_console="f8", skip_list=[]):
    """Executa o ciclo completo do macro de visão."""
    try:
        if not get_running_status(): return

        # --- PASSO 1: INVOCAR COMANDO ---
        status_widget.configure(text="Invocando Comando...", text_color="yellow")
        pyautogui.press(tecla_console)
        time.sleep(0.2)
        
        pyautogui.write(comando, interval=0.01)
        time.sleep(0.1)
        pyautogui.press('enter')
        time.sleep(0.1)
        pyautogui.press(tecla_console) 
        time.sleep(1.0) # Espera o minigame carregar

        # --- PASSO 2: IDENTIFICAR PADRÃO ---
        status_widget.configure(text="Escaneando Tela...", text_color="cyan")
        nome_padrao = identificar_padrao_na_tela()

        if nome_padrao in skip_list:
            status_widget.configure(text=f"IGNORANDO: {nome_padrao}", text_color="#f39c12")
            pyautogui.press('esc')
            return

        if not nome_padrao:
            status_widget.configure(text="Padrão não encontrado", text_color="red")
            pyautogui.press('esc')
            return

        # --- PASSO 3: CARREGAR DADOS ---
        if not os.path.exists("coordenadas_calibradas.json"):
            status_widget.configure(text="Erro: JSON ausente", text_color="red")
            return
            
        with open("coordenadas_calibradas.json", "r", encoding='utf-8') as f:
            all_data = json.load(f)
        
        config = all_data.get(nome_padrao)
        if not config or "points" not in config:
            pyautogui.press('esc')
            return

        points = config["points"]
        if not points: return

        # Normalização do ponto inicial
        p0 = points[0]
        start_x = (p0[0] if isinstance(p0, list) else p0["x"]) + ROI_OFFSET_X
        start_y = p0[1] if isinstance(p0, list) else p0["y"]

        # --- PASSO 4: EXECUÇÃO DO RASTRO ---
        status_widget.configure(text=f"Executando: {nome_padrao}", text_color="#FF8C00")
        pyautogui.moveTo(start_x, start_y, duration=0.15) 
        
        if not get_running_status(): return

        # Sequência de ativação
        pyautogui.press('x') 
        time.sleep(0.8) 
        
        pyautogui.mouseDown()
        for p in points[1:]:
            if not get_running_status():
                pyautogui.mouseUp()
                return
                
            curr_x = (p[0] if isinstance(p, list) else p["x"]) + ROI_OFFSET_X
            curr_y = p[1] if isinstance(p, list) else p["y"]
            
            pyautogui.moveTo(curr_x, curr_y)
            
            # Teclas específicas embutidas no rastro (opcional)
            if isinstance(p, dict) and p.get("key"):
                pyautogui.press(p["key"])

            wait_time = p.get("wait", 0.005) if isinstance(p, dict) else 0.005
            time.sleep(max(0, wait_time))

        pyautogui.mouseUp()

        # --- PASSO 5: VALIDAÇÃO DINÂMICA ---
        status_widget.configure(text="Validando...", text_color="green")
        
        sucesso_detectado = False
        timeout = time.time() + 2.5
        while time.time() < timeout:
            if not get_running_status(): return
            if capturar_brilho() > 90: # Limiar de brilho para sucesso
                sucesso_detectado = True
                break
            time.sleep(0.05)

        if sucesso_detectado:
            stats_callback('sucessos')
            status_widget.configure(text="Sucesso!", text_color="green")
        else:
            stats_callback('fracassos')
            status_widget.configure(text="Fracasso ou Timeout", text_color="red")
            pyautogui.press('esc')

    except Exception as e:
        logging.exception("Erro no vision_engine:")
        pyautogui.press('esc')
        status_widget.configure(text="Erro Crítico", text_color="red")