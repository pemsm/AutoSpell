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
SAMPLING_RATE = 0.01  # 100Hz
ROI_OFFSET_X = 960 

def gravar_movimento(nome_magia):
    pontos_gravados = []
    # Monitoramos estas teclas durante o desenho
    teclas_game = ['c', 'x', 'z']
    
    print(f"\n--- Gravador de Rastro: {nome_magia} ---")
    print(f"1. Posicione o mouse no início do desenho.")
    print(f"2. Pressione [{TECLA_INICIAR.upper()}] para iniciar.")
    
    keyboard.wait(TECLA_INICIAR)
    
    print(">> [GRAVANDO] - Desenhe agora!")
    print(">> DICA: Se o desenho exige apertar C, X ou Z, aperte-as enquanto grava!")
    print(f">> Pressione [{TECLA_TERMINAR.upper()}] para encerrar.")
    
    last_check = time.time()
    
    try:
        while not keyboard.is_pressed(TECLA_TERMINAR):
            agora = time.time()
            
            if agora - last_check >= SAMPLING_RATE:
                x, y = pyautogui.position()
                dt = round(agora - last_check, 4)
                
                # Detectar se alguma tecla de ação está sendo pressionada NO MOMENTO
                tecla_ativa = None
                for t in teclas_game:
                    if keyboard.is_pressed(t):
                        tecla_ativa = t
                        break
                
                # Salva o ponto com suporte a tecla (compatível com vision_engine)
                pontos_gravados.append({
                    "x": int(x - ROI_OFFSET_X),
                    "y": int(y),
                    "wait": dt,
                    "key": tecla_ativa
                })
                last_check = agora
            
            time.sleep(0.001) 
            
    except KeyboardInterrupt:
        pass

    if pontos_gravados:
        pontos_gravados[0]["wait"] = 0

    print(f"\n✅ Captura finalizada! {len(pontos_gravados)} pontos registrados.")
    return pontos_gravados

def salvar_calibracao(nome, pontos):
    arquivo = "coordenadas_calibradas.json"
    dados = {}
    
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding='utf-8') as f:
                dados = json.load(f)
        except:
            dados = {}
            
    # Salva usando o nome EXATO do padrão (ex: fireball.png)
    dados[nome] = {"points": pontos}
    
    with open(arquivo, "w", encoding='utf-8') as f:
        json.dump(dados, f, indent=4)
    print(f"💾 Magia '{nome}' salva com sucesso em '{arquivo}'!")

def listar_padroes_disponiveis():
    if not os.path.exists("padroes"):
        return []
    return [f for f in os.listdir("padroes") if f.lower().endswith(('.png', '.jpg'))]

if __name__ == "__main__":
    padroes = listar_padroes_disponiveis()
    
    if not padroes:
        print("❌ Nenhuma imagem encontrada na pasta 'padroes'.")
        print("Coloque os prints dos feitiços lá antes de gravar os rastros.")
    else:
        print("\nPadroes detectados:")
        for i, p in enumerate(padroes):
            print(f"{i+1}. {p}")
        
        escolha = input("\nEscolha o número do padrão ou digite o nome completo: ").strip()
        
        nome_final = ""
        if escolha.isdigit() and int(escolha) <= len(padroes):
            nome_final = padroes[int(escolha)-1]
        else:
            nome_final = escolha

        if nome_final:
            rastros = gravar_movimento(nome_final)
            if len(rastros) > 10:
                salvar_calibracao(nome_final, rastros)
            else:
                print("❌ Gravação muito curta.")