import sys
import os
import json

# Adiciona o diretório atual ao PATH para evitar problemas de importação
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from ui.login_window import LoginWindow
except ImportError as e:
    print(f"❌ Erro ao importar a interface de login: {e}")
    print("Certifique-se de que a pasta 'ui' contém o arquivo 'login_window.py'.")
    sys.exit(1)

def carregar_configuracoes():
    """Carrega o settings.json para garantir que a detecção de XP tenha os dados necessários."""
    caminho_settings = os.path.abspath(os.path.join("data", "settings.json"))
    if os.path.exists(caminho_settings):
        try:
            with open(caminho_settings, "r", encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao ler settings.json: {e}")
    
    # Configurações padrão caso o arquivo falhe ou não exista
    return {
        "skip_list": ["minhoca.png"],
        "detection": {
            "success_roi": {"x": 1540, "y": 490, "w": 360, "h": 80},
            "threshold_value": 210,
            "min_white_pixels": 400,
            "detection_timeout": 5.0
        }
    }

def main():
    """
    Função principal que inicia o fluxo do AutoSpell.
    O fluxo segue: autospell.py -> LoginWindow -> (Auth Sucesso) -> AutoSpellApp
    """
    try:
        # 1. Carrega as configurações de detecção e padrões
        config_data = carregar_configuracoes()
        
        # 2. Instancia a janela de login. 
        # Passamos as configurações carregadas para que a aplicação principal as receba após o login.
        app = LoginWindow()
        
        # Atribuímos as configurações à instância para que ela possa repassar 
        # ao AutoSpellApp (main_app.py) no momento da transição.
        app.settings_config = config_data
        
        app.mainloop()
        
    except KeyboardInterrupt:
        print("\n[!] Programa encerrado pelo usuário.")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Erro crítico ao iniciar a aplicação: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()