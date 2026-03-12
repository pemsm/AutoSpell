import sys
import os

# Adiciona o diretório atual ao PATH para evitar problemas de importação de módulos internos
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from ui.login_window import LoginWindow
except ImportError as e:
    print(f"❌ Erro ao importar a interface de login: {e}")
    print("Certifique-se de que a pasta 'ui' contém o arquivo 'login_window.py'.")
    sys.exit(1)

def main():
    """
    Função principal que inicia o fluxo do Wizard HUD.
    O fluxo segue: autospell.py -> LoginWindow -> (Auth Sucesso) -> AutoSpellApp
    """
    try:
        # Instancia a janela de login. 
        # A lógica de KeyAuth e a transição para o App principal já estão dentro dela.
        app = LoginWindow()
        app.mainloop()
        
    except KeyboardInterrupt:
        # Permite fechar o processo via Ctrl+C no terminal sem disparar traceback
        print("\n[!] Programa encerrado pelo usuário.")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Erro crítico ao iniciar a aplicação: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()