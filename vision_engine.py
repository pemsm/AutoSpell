import os
import time
import pyautogui
import json
import numpy as np
from PIL import ImageGrab

# Configurações de Tela (Devem ser as mesmas do main.py)
SCREEN_W = 1920
SCREEN_H = 1080

def capturar_brilho():
    """Mede a luminosidade média da tela para detectar transições (abertura do minigame)."""
    img = np.array(ImageGrab.grab())
    return np.mean(img)

def run_macro(comando, status_widget, stats_callback, tecla_console="f8"):
    try:
        # --- 1. FLUXO DE CONSOLE E COMANDO ---
        status_widget.configure(text=f"Status: Abrindo {tecla_console}...", text_color="yellow")
        pyautogui.press(tecla_console)
        time.sleep(0.3)
        
        pyautogui.write(comando)
        pyautogui.press('enter')
        time.sleep(0.3)
        
        # Fecha o console
        pyautogui.press(tecla_console)
        
        # --- 2. AGUARDA O MINIGAME CARREGAR ---
        status_widget.configure(text="Status: Aguardando tela escurecer...", text_color="cyan")
        timeout = time.time() + 8
        while capturar_brilho() > 85: # Enquanto a tela estiver clara, espera
            if time.time() > timeout:
                status_widget.configure(text="Erro: Minigame não abriu", text_color="red")
                return
            time.sleep(0.1)
        
        # Delay de garantia para estabilização visual (500ms conforme solicitado)
        time.sleep(0.5)

        # --- 3. CARREGA DADOS DE CALIBRAÇÃO ---
        if not os.path.exists("coordenadas_calibradas.json"):
            status_widget.configure(text="Erro: Arquivo JSON não encontrado!", text_color="red")
            return
            
        with open("coordenadas_calibradas.json", "r") as f:
            all_data = json.load(f)
        
        if not all_data:
            status_widget.configure(text="Erro: JSON vazio!", text_color="red")
            return

        # Seleciona o primeiro padrão disponível (ou lógica de seleção futura)
        pattern_name = list(all_data.keys())[0]
        config = all_data[pattern_name]
        
        points = config["points"]
        duration = config["duration_ms"] / 1000 # Converte ms para segundos
        
        if not points or len(points) < 2:
            status_widget.configure(text="Erro: Pontos insuficientes!", text_color="red")
            return

        # --- 4. POSICIONAMENTO INICIAL ---
        # Move para o Ponto 1 antes de apertar X
        ponto_inicial = points[0]
        status_widget.configure(text="Status: Posicionando Mouse...", text_color="white")
        pyautogui.moveTo(ponto_inicial[0], ponto_inicial[1], duration=0.4)
        time.sleep(0.2)

        # --- 5. INÍCIO DO MINIGAME (TECLA X) ---
        status_widget.configure(text="Status: Iniciando (X)...", text_color="#00FF00")
        pyautogui.press('x')
        time.sleep(0.3) # Pequeno delay para o jogo registrar o início do traçado

        # --- 6. EXECUÇÃO DO TRAÇADO ---
        pyautogui.mouseDown()
        
        # Calcula o tempo por segmento para manter a velocidade constante definida no slider
        time_per_segment = duration / (len(points) - 1)
        
        for i in range(1, len(points)):
            proximo_ponto = points[i]
            # Move suavemente entre os pontos calibrados
            pyautogui.moveTo(
                proximo_ponto[0], 
                proximo_ponto[1], 
                duration=time_per_segment, 
                tween=pyautogui.linear
            )

        pyautogui.mouseUp()

        # --- 7. FINALIZAÇÃO E LOG ---
        status_widget.configure(text="Status: Aguardando animação final...", text_color="gray")
        
        # Animação dura entre 1-3 segundos (usando 3 de garantia conforme solicitado)
        time.sleep(3.0)
        
        # Verifica se o minigame fechou (brilho volta ao normal)
        if capturar_brilho() > 90:
            stats_callback('sucessos')
            status_widget.configure(text="Status: Sucesso!", text_color="green")
        else:
            # Se a tela continuar escura, algo deu errado no traçado
            stats_callback('fracassos')
            status_widget.configure(text="Status: Falha no traçado", text_color="red")

    except Exception as e:
        status_widget.configure(text=f"Erro Crítico: {str(e)}", text_color="red")