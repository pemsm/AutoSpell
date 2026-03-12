import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import os
import sys
from core.keyauth import api
from utils.config_manager import get_checksum

# --- INSTANCIAÇÃO DA API ---
# Agora com o Application Secret incluído para validar a sessão corretamente
keyauthapp = api(
    name = "Wizard HUD - Ghost Edition", 
    ownerid = "TqGr3LrSGL", 
    secret = "6ff2f897fdbdc2dbf6a00982d49b68331572cd23f7b3117aefd5c11d9b602f4a",
    version = "1.1.0",
    hash_to_check = get_checksum()
)

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wizard HUD - Autenticação")
        self.geometry("400x550")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        
        # Garante que ao fechar no 'X', o processo encerre completamente
        self.protocol("WM_DELETE_WINDOW", self.fechar_completo)
        
        self.is_register_mode = False

        # --- UI ELEMENTS ---
        self.label = ctk.CTkLabel(self, text="WIZARD HUD", font=("Arial", 28, "bold"), text_color="#00FFFF")
        self.label.pack(pady=(30, 5))
        
        self.subtitle = ctk.CTkLabel(self, text="GHOST EDITION", font=("Arial", 12))
        self.subtitle.pack(pady=(0, 20))

        self.entry_user = ctk.CTkEntry(self, placeholder_text="Usuário", width=300, height=40)
        self.entry_user.pack(pady=10)

        self.entry_pass = ctk.CTkEntry(self, placeholder_text="Senha", width=300, height=40, show="*")
        self.entry_pass.pack(pady=10)

        self.entry_key = ctk.CTkEntry(self, placeholder_text="Chave de Ativação (License)", width=300, height=40)
        
        self.btn_action = ctk.CTkButton(self, text="ENTRAR", fg_color="#1f538d", hover_color="#14375e", height=45, command=self.executar_auth)
        self.btn_action.pack(pady=(20, 10))

        self.btn_toggle = ctk.CTkButton(self, text="Não tem conta? Criar conta", fg_color="transparent", text_color="gray", command=self.toggle_mode)
        self.btn_toggle.pack()

        self.status_label = ctk.CTkLabel(self, text="Conectando...", text_color="gray")
        self.status_label.pack(pady=20)

        # Inicia a conexão com servidor em background
        threading.Thread(target=self.iniciar_keyauth, daemon=True).start()

    def fechar_completo(self):
        self.destroy()
        os._exit(0)

    def toggle_mode(self):
        self.is_register_mode = not self.is_register_mode
        if self.is_register_mode:
            self.entry_key.pack(pady=10, after=self.entry_pass)
            self.btn_action.configure(text="REGISTRAR E ATIVAR")
            self.btn_toggle.configure(text="Já possui conta? Faça Login")
        else:
            self.entry_key.pack_forget()
            self.btn_action.configure(text="ENTRAR")
            self.btn_toggle.configure(text="Não tem conta? Criar conta")

    def iniciar_keyauth(self):
        try:
            # Chama o init que agora envia o secret corretamente
            keyauthapp.init()
            if keyauthapp.initialized:
                self.after(0, lambda: self.status_label.configure(text="Servidor Online", text_color="green"))
            else:
                self.after(0, lambda: self.status_label.configure(text="Erro: Aplicação Inválida", text_color="red"))
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"Erro de Conexão: {e}", text_color="red"))

    def executar_auth(self):
        user = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        key = self.entry_key.get().strip()

        if not user or not password:
            self.status_label.configure(text="Preencha usuário e senha!", text_color="orange")
            return

        self.btn_action.configure(state="disabled")
        self.status_label.configure(text="Processando...", text_color="yellow")

        def auth_thread():
            try:
                if self.is_register_mode:
                    if not key:
                        self.after(0, lambda: [self.status_label.configure(text="Insira a License Key!", text_color="orange"), self.btn_action.configure(state="normal")])
                        return
                    success, msg = keyauthapp.register(user, password, key)
                else:
                    success, msg = keyauthapp.login(user, password)

                if success:
                    self.after(0, lambda: self.status_label.configure(text=f"Sucesso: {msg}", text_color="green"))
                    self.after(500, self.liberar_acesso)
                else:
                    self.after(0, lambda m=msg: [self.status_label.configure(text=f"Erro: {m}", text_color="red"), self.btn_action.configure(state="normal")])
            except Exception as e:
                self.after(0, lambda err=str(e): [self.status_label.configure(text=f"Erro Técnico: {err}", text_color="red"), self.btn_action.configure(state="normal")])

        threading.Thread(target=auth_thread, daemon=True).start()

    def liberar_acesso(self):
        """Fecha a janela de login e abre a aplicação principal."""
        self.withdraw()
        # Import local para evitar erro de importação circular
        from ui.main_app import AutoSpellApp 
        app = AutoSpellApp(auth_instance=keyauthapp)
        app.mainloop()
        self.destroy()