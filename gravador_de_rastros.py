import pyautogui
import json
import time
import keyboard 
import os

# ==========================================
# CONFIGURAÇÕES
# ==========================================
TECLA_INICIAR = 'f7'
TECLA_TERMINAR = 'f8'
SAMPLING_RATE = 0.01  # 100Hz é o ideal para movimentos suaves
# Importante: ROI_OFFSET_X deve ser igual ao do seu App principal
ROI_OFFSET_X = 960 

def gravar_movimento(nome_magia):
    pontos_gravados = []
    print(f"\n--- Gravador de Rastro: {nome_magia} ---")
    print(f"1. Posicione o mouse onde a magia começa.")
    print(f"2. Pressione [{TECLA_INICIAR.upper()}] para iniciar.")
    
    # Bloqueia a execução até a tecla ser pressionada
    keyboard.wait(TECLA_INICIAR)
    
    print(">> [GRAVANDO] - Desenhe agora! (Pressione F8 para parar)")
    
    start_time = time.time()
    last_check = start_time
    
    try:
        while not keyboard.is_pressed(TECLA_TERMINAR):
            agora = time.time()
            
            if agora - last_check >= SAMPLING_RATE:
                x, y = pyautogui.position()
                
                # Normalização: Salvamos a posição relativa ao centro/offset
                # Isso permite que o macro funcione mesmo se a janela mudar de lugar
                rel_x = x - ROI_OFFSET_X
                
                pontos_gravados.append({
                    "x": int(rel_x),
                    "y": int(y),
                    "wait": round(agora - last_check, 4)
                })
                last_check = agora
            
            # Pequena pausa para não fritar o processador
            time.sleep(0.001) 
            
    except KeyboardInterrupt:
        pass

    # Ajuste fino: O primeiro ponto não deve esperar para ser executado
    if pontos_gravados:
        pontos_gravados[0]["wait"] = 0

    print(f"\n✅ Captura finalizada! {len(pontos_gravados)} pontos registrados.")
    return pontos_gravados

def salvar_calibracao(nome, pontos):
    arquivo = "coordenadas_calibradas.json"
    dados = {}
    
    # Carrega dados existentes para não sobrescrever outras magias já salvas
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding='utf-8') as f:
                dados = json.load(f)
        except json.JSONDecodeError:
            dados = {}
            
    # Adiciona ou atualiza a magia no dicionário
    dados[nome] = {"points": pontos}
    
    with open(arquivo, "w", encoding='utf-8') as f:
        json.dump(dados, f, indent=4)
    print(f"💾 Arquivo '{arquivo}' atualizado!")

if __name__ == "__main__":
    # Garante que o nome seja limpo (sem extensões se você preferir)
    nome = input("Digite o nome da magia (ex: fireball): ").strip()
    
    if nome:
        rastros = gravar_movimento(nome)
        if len(rastros) > 10: # Evita salvar cliques acidentais
            salvar_calibracao(nome, rastros)
        else:
            print("❌ Erro: Gravação muito curta ou vazia.")
    else:
        print("❌ Nome inválido.")