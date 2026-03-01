import customtkinter as ctk
import threading
from vision_engine import run_macro

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wizard Automator - FiveM")
        self.geometry("400x300")

        self.label = ctk.CTkLabel(self, text="Configuração de Feitiço", font=("Roboto", 20))
        self.label.pack(pady=20)

        # Input do Comando (m11, m12, etc)
        self.cmd_entry = ctk.CTkEntry(self, placeholder_text="Comando F8 (ex: m11)")
        self.cmd_entry.pack(pady=10)

        # Botão Start
        self.start_btn = ctk.CTkButton(self, text="Iniciar Treino", command=self.start_thread)
        self.start_btn.pack(pady=20)

        self.status_label = ctk.CTkLabel(self, text="Status: Aguardando...", text_color="gray")
        self.status_label.pack(pady=10)

    def start_thread(self):
        comando = self.cmd_entry.get()
        # Roda em thread separada para não travar a janela
        t = threading.Thread(target=run_macro, args=(comando, self.status_label))
        t.start()

if __name__ == "__main__":
    app = App()
    app.mainloop()