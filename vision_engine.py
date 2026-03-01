import pyautogui
import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

def run_macro(comando, status_widget):
    status_widget.configure(text="Status: Abrindo Console...", text_color="yellow")
    
    # Fluxo F8
    pyautogui.press('f8')
    time.sleep(0.2)
    pyautogui.write(comando)
    pyautogui.press('enter')
    time.sleep(1)
    pyautogui.press('x') # Inicia o minigame
    
    status_widget.configure(text="Status: Analisando com NVIDIA NIM...", text_color="blue")
    
    # Aqui você capturaria a tela e enviaria para o NIM
    # O modelo retornaria os pontos do 'Z' ou do padrão atual
    # Exemplo de movimento fictício baseado nos pontos:
    pontos = [(500, 300), (800, 300), (500, 600), (800, 600)] # Coordenadas exemplo
    
    for x, y in pontos:
        pyautogui.moveTo(x, y, duration=0.8, tween=pyautogui.easeInOutQuad)
    
    status_widget.configure(text="Status: Concluído!", text_color="green")