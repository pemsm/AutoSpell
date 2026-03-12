import customtkinter as ctk
import tkinter as tk  
from tkinter import messagebox # Import necessário para o alerta visual
import threading
import time
import keyboard
import pyautogui
import os
import json
import logging
import hashlib
import sys
from PIL import Image, ImageTk
from vision_engine import run_macro
from keyauth import api 

# --- GARANTIA DE DIRETÓRIO ---
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    filename='debug_log.txt',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# --- CONFIGURAÇÕES DE TELA ---
SCREEN_W = 1920
SCREEN_H = 1080
ROI_OFFSET_X = 960 
SAMPLING_RATE = 0.01

def getchecksum():
    md5_hash = hashlib.md5()
    path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    try:
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                md5_hash.update(byte_block)
        return md5_hash.hexdigest()
    except Exception as e:
        logging.error(f"Erro no Checksum: {e}")
        return ""

# --- INICIALIZAÇÃO SEGURA DO KEYAUTH ---
# Envolvemos em um try/except para que o erro de versão não feche o terminal sem aviso
try:
    keyauthapp = api(
        name = "Wizard HUD - Ghost Edition", 
        ownerid = "TqGr3LrSGL", 
        version = "1.1.0", # Versão atualizada conforme o painel
        hash_to_check = getchecksum()
    )
except Exception as e:
    # Se der erro de versão ou conexão, mostra a caixa de mensagem antes de fechar
    root_temp = tk.Tk()
    root_temp.withdraw()
    messagebox.showerror("Erro de Inicialização", f"Ocorreu um erro ao conectar ao servidor:\n\n{e}\n\nVerifique sua conexão ou se a versão (1.1.0) está correta.")
    os._exit(1)

# --- JANELA DE LOGIN & REGISTRO ---
class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wizard HUD - Autenticação")
        self.geometry("400x550")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.fechar_completo)
        
        self.is_register_mode = False

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

        threading.Thread(target=self.iniciar_keyauth, daemon=True).start()

    def fechar_completo(self):
        try: keyboard.unhook_all()
        except: pass
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
            keyauthapp.init()
            if keyauthapp.initialized:
                self.after(0, lambda: self.status_label.configure(text="Servidor Online", text_color="green"))
            else:
                self.after(0, lambda: self.status_label.configure(text="Erro: Aplicação Inválida", text_color="red"))
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"Erro de Conexão: {e}", text_color="red"))

    def executar_auth(self):
        user = self.entry_user.get()
        password = self.entry_pass.get()
        key = self.entry_key.get()

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
        self.withdraw()
        app = App()
        app.mainloop()
        self.destroy()

# --- APLICAÇÃO PRINCIPAL (HUD) ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wizard HUD - Ghost Edition")
        self.geometry("950x850") 
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.fechar_completo)
        
        self.running = False
        self.hud_active = False
        self.full_calib_active = False
        self.recording = False
        self.is_playing_preview = False
        self.show_points_active = False 
        self.tk_img = None 
        
        self.last_food_time = 0
        self.last_drink_time = 0
        self.start_session_time = 0
        
        self.calibration_file = "coordenadas_calibradas.json"
        self.settings_file = "settings.json"
        self.points_data = self.load_calibration()
        self.skip_list = self.load_settings() 
        
        self.current_editing_pattern = None
        self.temp_points = [] 
        self.stats = {"sucessos": 0, "fracassos": 0, "total": 0}

        # --- UI SETUP ---
        self.tabview = ctk.CTkTabview(self, width=930, height=800)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.tab_main = self.tabview.add("Automação")
        self.tab_calibrate = self.tabview.add("Gravar Movimento")
        self.tab_skip = self.tabview.add("Skip List") 

        self.setup_main_tab()
        self.setup_calibrate_tab()
        self.setup_skip_tab() 

        # Hotkeys
        keyboard.add_hotkey('f6', self.trigger_f6)
        keyboard.add_hotkey('f7', self.trigger_f7)
        keyboard.add_hotkey('f9', self.trigger_f9)
        
        threading.Thread(target=self.listen_hotkeys, daemon=True).start()

    def fechar_completo(self):
        self.running = False
        try: keyboard.unhook_all()
        except: pass
        self.destroy()
        os._exit(0)

    def setup_main_tab(self):
        self.status_label = ctk.CTkLabel(self.tab_main, text="AGUARDANDO START (F5)", font=("Arial", 24, "bold"), text_color="#555")
        self.status_label.pack(pady=(10, 5))

        self.stats_frame = ctk.CTkFrame(self.tab_main, fg_color="#1a1a1a", corner_radius=10)
        self.stats_frame.pack(pady=5, padx=20, fill="x")
        
        self.lbl_suc = ctk.CTkLabel(self.stats_frame, text="✅ Sucessos: 0", font=("Arial", 16), text_color="#2ecc71")
        self.lbl_suc.pack(side="left", expand=True, pady=10)
        self.lbl_fail = ctk.CTkLabel(self.stats_frame, text="❌ Falhas: 0", font=("Arial", 16), text_color="#e74c3c")
        self.lbl_fail.pack(side="left", expand=True, pady=10)
        self.lbl_total = ctk.CTkLabel(self.stats_frame, text="📊 Total: 0", font=("Arial", 16), text_color="#3498db")
        self.lbl_total.pack(side="left", expand=True, pady=10)

        self.frame_inputs = ctk.CTkFrame(self.tab_main)
        self.frame_inputs.pack(pady=10, padx=20, fill="both")
        self.frame_inputs.grid_columnconfigure((1, 3), weight=1)

        teclas_f = [f"f{i}" for i in range(1, 13)]
        teclas_num = [str(i) for i in range(1, 6)]
        tempos = ["Desativado", "10", "15", "30", "45", "60", "90", "120"]

        ctk.CTkLabel(self.frame_inputs, text="Tecla Console:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.combo_tecla_console = ctk.CTkComboBox(self.frame_inputs, values=teclas_f, width=120)
        self.combo_tecla_console.set("f8")
        self.combo_tecla_console.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self.frame_inputs, text="Atalho ON/OFF:").grid(row=0, column=2, padx=10, pady=5, sticky="e")
        self.combo_hotkey = ctk.CTkComboBox(self.frame_inputs, values=teclas_f, width=120)
        self.combo_hotkey.set("f5")
        self.combo_hotkey.grid(row=0, column=3, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self.frame_inputs, text="Comando Feitiço:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.entry_comando = ctk.CTkEntry(self.frame_inputs, width=120)
        self.entry_comando.insert(0, "m11")
        self.entry_comando.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self.frame_inputs, text="Tecla Comida:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.combo_key_food = ctk.CTkComboBox(self.frame_inputs, values=teclas_num, width=120)
        self.combo_key_food.set("1")
        self.combo_key_food.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self.frame_inputs, text="Intervalo Comida (Min):").grid(row=2, column=2, padx=10, pady=5, sticky="e")
        self.combo_time_food = ctk.CTkComboBox(self.frame_inputs, values=tempos, width=120)
        self.combo_time_food.set("15")
        self.combo_time_food.grid(row=2, column=3, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self.frame_inputs, text="Tecla Bebida:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.combo_key_drink = ctk.CTkComboBox(self.frame_inputs, values=teclas_num, width=120)
        self.combo_key_drink.set("2")
        self.combo_key_drink.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self.frame_inputs, text="Intervalo Bebida (Min):").grid(row=3, column=2, padx=10, pady=5, sticky="e")
        self.combo_time_drink = ctk.CTkComboBox(self.frame_inputs, values=tempos, width=120)
        self.combo_time_drink.set("10")
        self.combo_time_drink.grid(row=3, column=3, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self.frame_inputs, text="Fechar Jogo (Min):").grid(row=4, column=0, padx=10, pady=5, sticky="e")
        self.entry_quit_game = ctk.CTkEntry(self.frame_inputs, width=120)
        self.entry_quit_game.insert(0, "0")
        self.entry_quit_game.grid(row=4, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self.frame_inputs, text="Desligar PC (Min):").grid(row=4, column=2, padx=10, pady=5, sticky="e")
        self.entry_shutdown_pc = ctk.CTkEntry(self.frame_inputs, width=120)
        self.entry_shutdown_pc.insert(0, "0")
        self.entry_shutdown_pc.grid(row=4, column=3, padx=10, pady=5, sticky="w")

        self.btn_hud = ctk.CTkButton(self.tab_main, text="ATIVAR MODO HUD COMPACTO", fg_color="#1f538d", height=45, command=self.toggle_hud_mode)
        self.btn_hud.pack(pady=10)

    def macro_loop(self):
        cmd = self.entry_comando.get()
        console = self.combo_tecla_console.get()
        self.start_session_time = time.time()
        self.last_food_time = time.time()
        self.last_drink_time = time.time()
        
        while self.running:
            agora = time.time()
            decorrido_min = (agora - self.start_session_time) / 60

            try:
                min_quit = int(self.entry_quit_game.get())
                min_shut = int(self.entry_shutdown_pc.get())
                if min_quit > 0 and decorrido_min >= min_quit:
                    os.system("taskkill /f /im ProjectZomboid64.exe")
                    self.running = False; break
                if min_shut > 0 and decorrido_min >= min_shut:
                    os.system("shutdown /s /t 60")
                    self.running = False; break
            except: pass

            def dual_status_update(texto, text_color=None):
                if self.winfo_exists():
                    self.after(0, lambda: self.status_label.configure(text=texto, text_color=text_color if text_color else "#555"))
                if self.hud_active and hasattr(self, 'hud_status_label') and self.hud_status_label.winfo_exists():
                    self.after(0, lambda: self.hud_status_label.configure(text=texto, text_color=text_color if text_color else "white"))

            class StatusProxy:
                def configure(self, **kwargs):
                    if "text" in kwargs: dual_status_update(kwargs["text"], kwargs.get("text_color"))

            def check_survival(last_time, combo_min, key, nome):
                if combo_min.get() != "Desativado":
                    intervalo_sec = int(combo_min.get()) * 60
                    if time.time() - last_time >= intervalo_sec:
                        dual_status_update(f"USANDO {nome}...", "orange")
                        pyautogui.press(key); time.sleep(1.2)
                        return time.time()
                return last_time

            self.last_drink_time = check_survival(self.last_drink_time, self.combo_time_drink, self.combo_key_drink.get(), "BEBIDA")
            self.last_food_time = check_survival(self.last_food_time, self.combo_time_food, self.combo_key_food.get(), "COMIDA")

            run_macro(comando=cmd, status_widget=StatusProxy(), stats_callback=self.update_stats, 
                      get_running_status=lambda: self.running, tecla_console=console, skip_list=self.skip_list)
            if not self.running: break

    def setup_skip_tab(self):
        self.skip_container = ctk.CTkFrame(self.tab_skip, fg_color="transparent")
        self.skip_container.pack(fill="both", expand=True, padx=20, pady=20)
        self.frame_avail = ctk.CTkFrame(self.skip_container)
        self.frame_avail.pack(side="left", fill="both", expand=True, padx=10)
        self.list_available = tk.Listbox(self.frame_avail, bg="#2b2b2b", fg="white", selectbackground="#1f538d", borderwidth=0, font=("Arial", 12))
        self.list_available.pack(fill="both", expand=True, padx=5, pady=5)
        self.frame_mid = ctk.CTkFrame(self.skip_container, fg_color="transparent")
        self.frame_mid.pack(side="left", padx=10)
        ctk.CTkButton(self.frame_mid, text="Adicionar >>", width=100, command=self.add_to_skip).pack(pady=10)
        ctk.CTkButton(self.frame_mid, text="<< Remover", width=100, command=self.remove_from_skip).pack(pady=10)
        self.frame_skip = ctk.CTkFrame(self.skip_container)
        self.frame_skip.pack(side="left", fill="both", expand=True, padx=10)
        self.list_skipped = tk.Listbox(self.frame_skip, bg="#2b2b2b", fg="#ff4444", selectbackground="#1f538d", borderwidth=0, font=("Arial", 12))
        self.list_skipped.pack(fill="both", expand=True, padx=5, pady=5)
        self.refresh_skip_ui()

    def refresh_skip_ui(self):
        self.list_available.delete(0, tk.END)
        self.list_skipped.delete(0, tk.END)
        self.update_pattern_list()
        for p in self.pattern_files:
            if p in self.skip_list: self.list_skipped.insert(tk.END, p)
            else: self.list_available.insert(tk.END, p)

    def add_to_skip(self):
        items = self.list_available.curselection()
        for i in items:
            name = self.list_available.get(i)
            if name not in self.skip_list: self.skip_list.append(name)
        self.save_settings(); self.refresh_skip_ui()

    def remove_from_skip(self):
        items = self.list_skipped.curselection()
        for i in items:
            name = self.list_skipped.get(i)
            if name in self.skip_list: self.skip_list.remove(name)
        self.save_settings(); self.refresh_skip_ui()

    def save_settings(self):
        with open(self.settings_file, "w") as f: json.dump({"skip_list": self.skip_list}, f)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f: return json.load(f).get("skip_list", [])
            except: return []
        return []

    def setup_calibrate_tab(self):
        self.canvas = ctk.CTkCanvas(self.tab_calibrate, width=SCREEN_W, height=SCREEN_H, bg="black", highlightthickness=0)
        self.canvas.place(x=0, y=0)
        self.ctrl_panel = ctk.CTkFrame(self.tab_calibrate, fg_color="#1a1a1a", border_width=2, border_color="#444")
        self.ctrl_panel.place(relx=0.02, rely=0.05, relwidth=0.35, relheight=0.7)
        ctk.CTkLabel(self.ctrl_panel, text="GRAVADOR DE RASTRO", font=("Arial", 18, "bold"), text_color="#00FFFF").pack(pady=10)
        self.update_pattern_list()
        self.combo_patterns = ctk.CTkComboBox(self.ctrl_panel, values=self.pattern_files, command=self.load_pattern_to_canvas, width=250)
        self.combo_patterns.pack(pady=10)
        self.lbl_rec_status = ctk.CTkLabel(self.ctrl_panel, text="F6: Rec | F7: Stop | F9: Modo HUD", font=("Arial", 13))
        self.lbl_rec_status.pack(pady=15)
        ctk.CTkButton(self.ctrl_panel, text="💾 SALVAR", fg_color="#27ae60", command=self.save_calibration).pack(pady=5)
        self.btn_preview = ctk.CTkButton(self.ctrl_panel, text="👁 VER RASTRO", fg_color="#555", command=self.toggle_preview_visuals)
        self.btn_preview.pack(pady=5)
        ctk.CTkButton(self.ctrl_panel, text="🖥 MODO HUD GRAVAÇÃO (F9)", fg_color="#d35400", command=self.toggle_full_calibration).pack(pady=5)

    def trigger_f6(self):
        if not self.recording: self.after(0, self.start_recording)
    def trigger_f7(self):
        if self.recording: self.after(0, self.stop_recording)
    def trigger_f9(self):
        self.after(0, self.toggle_full_calibration)

    def start_recording(self):
        if not self.current_editing_pattern:
            self.update_rec_label("❌ SELECIONE PADRÃO", "#e74c3c")
            return
        self.recording = True; self.temp_points = []; self.canvas.delete("pt")
        self.update_rec_label("● GRAVANDO...", "#FF4444")
        threading.Thread(target=self.record_loop, daemon=True).start()

    def stop_recording(self):
        self.recording = False
        self.update_rec_label("✅ GRAVADO COM SUCESSO!", "#00FF00")
        self.show_points_active = True
        self.btn_preview.configure(text="❌ OCULTAR PREVIEWS", fg_color="#e74c3c")
        self.redraw_canvas(); self.start_ghost_preview()

    def toggle_preview_visuals(self):
        if not self.temp_points: return
        self.show_points_active = not self.show_points_active
        if self.show_points_active:
            self.btn_preview.configure(text="❌ OCULTAR PREVIEWS", fg_color="#e74c3c")
            self.redraw_canvas(); self.start_ghost_preview()
        else:
            self.btn_preview.configure(text="👁 VER RASTRO", fg_color="#555")
            self.canvas.delete("pt", "ghost")

    def update_rec_label(self, texto, cor):
        if hasattr(self, 'hud_rec_status') and self.hud_rec_status.winfo_exists():
            self.hud_rec_status.configure(text=texto, text_color=cor)
        else: self.lbl_rec_status.configure(text=texto, text_color=cor)

    def record_loop(self):
        last_check = time.time()
        while self.recording:
            agora = time.time()
            if agora - last_check >= SAMPLING_RATE:
                x, y = pyautogui.position()
                dt = round(agora - last_check, 4)
                tecla = None
                for t in ['c', 'x', 'z']:
                    if keyboard.is_pressed(t): tecla = t; break
                self.temp_points.append({"x": int(x - ROI_OFFSET_X), "y": int(y), "wait": dt, "key": tecla})
                last_check = agora; self.after(0, self.redraw_canvas)
            time.sleep(0.001)

    def redraw_canvas(self):
        cv = self.canvas_hud if (self.full_calib_active and hasattr(self, 'canvas_hud')) else self.canvas
        if not cv.winfo_exists(): return
        cv.delete("pt")
        if not self.temp_points or not self.show_points_active: return
        for p in self.temp_points:
            dx, dy = (p.get("x") + ROI_OFFSET_X, p.get("y"))
            cv.create_oval(dx-1, dy-1, dx+1, dy+1, fill="#00FFFF", outline="", tags="pt")

    def start_ghost_preview(self):
        if not self.temp_points or self.is_playing_preview: return
        threading.Thread(target=self.ghost_playback_thread, daemon=True).start()

    def ghost_playback_thread(self):
        self.is_playing_preview = True
        cv = self.canvas_hud if (self.full_calib_active and hasattr(self, 'canvas_hud')) else self.canvas
        if not cv.winfo_exists(): self.is_playing_preview = False; return
        ghost = cv.create_oval(0,0,0,0, fill="#00FF00", outline="white", width=2, tags="ghost")
        for p in self.temp_points:
            if not self.show_points_active or not cv.winfo_exists(): break
            dx, dy, wait = (p.get("x") + ROI_OFFSET_X, p.get("y"), p.get("wait", 0.01))
            cv.coords(ghost, dx-6, dy-6, dx+6, dy+6)
            time.sleep(wait)
        try: cv.delete("ghost")
        except: pass
        self.is_playing_preview = False

    def toggle_full_calibration(self):
        self.full_calib_active = not self.full_calib_active
        if self.full_calib_active:
            self.withdraw() 
            self.hud_window = ctk.CTkToplevel(self)
            self.hud_window.geometry(f"{SCREEN_W}x{SCREEN_H}+0+0")
            self.hud_window.overrideredirect(True)
            self.hud_window.attributes("-topmost", True, "-transparentcolor", "black")
            self.hud_window.config(bg="black")
            self.hud_rec_status = ctk.CTkLabel(self.hud_window, text="MODO GRAVAÇÃO: F6 (Start) | F7 (Stop) | F9 (Sair)", font=("Arial", 20, "bold"), text_color="yellow")
            self.hud_rec_status.pack(pady=50)
            self.canvas_hud = ctk.CTkCanvas(self.hud_window, width=SCREEN_W, height=SCREEN_H, bg="black", highlightthickness=0)
            self.canvas_hud.pack()
        else:
            if hasattr(self, 'hud_window'): self.hud_window.destroy()
            self.deiconify()

    def load_pattern_to_canvas(self, filename):
        self.current_editing_pattern = filename
        path = os.path.join("padroes", filename)
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            img.putalpha(img.getchannel('A').point(lambda i: i * 0.4))
            img = img.resize((SCREEN_W - ROI_OFFSET_X, SCREEN_H))
            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.delete("bg")
            self.canvas.create_image(ROI_OFFSET_X, 0, anchor="nw", image=self.tk_img, tags="bg")
        self.temp_points = self.points_data.get(filename, {}).get("points", [])
        self.show_points_active = False; self.canvas.delete("pt", "ghost")

    def toggle_hud_mode(self):
        if not self.hud_active:
            self.hud_active = True
            self.tabview.pack_forget() 
            self.update_idletasks()   
            
            self.geometry("400x250+10+10")
            self.attributes("-alpha", 0.8)
            
            self.hud_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
            self.hud_frame.pack(fill="both", expand=True)
            
            ctk.CTkLabel(self.hud_frame, text="WIZARD HUD", font=("Arial", 14, "bold"), text_color="#00FFFF").pack(pady=5)
            
            txt_atual = self.status_label.cget("text")
            self.hud_status_label = ctk.CTkLabel(self.hud_frame, text=txt_atual, font=("Arial", 16, "bold"))
            self.hud_status_label.pack(pady=10)
            
            ctk.CTkButton(self.hud_frame, text="VOLTAR (MENU)", height=25, command=self.toggle_hud_mode).pack(pady=10)
        else:
            self.hud_active = False
            if hasattr(self, 'hud_frame'): self.hud_frame.destroy()
            
            self.attributes("-alpha", 1.0)
            self.geometry("950x850")
            self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

    def update_stats(self, tipo):
        self.stats[tipo] += 1; self.stats["total"] += 1
        if self.winfo_exists():
            self.after(0, lambda: self.lbl_suc.configure(text=f"✅ Sucessos: {self.stats['sucessos']}"))
            self.after(0, lambda: self.lbl_fail.configure(text=f"❌ Falhas: {self.stats['fracassos']}"))
            self.after(0, lambda: self.lbl_total.configure(text=f"📊 Total: {self.stats['total']}"))

    def save_calibration(self):
        if self.current_editing_pattern:
            self.points_data[self.current_editing_pattern] = {"points": self.temp_points}
            with open(self.calibration_file, "w") as f: json.dump(self.points_data, f, indent=4)

    def load_calibration(self):
        if os.path.exists(self.calibration_file):
            try:
                with open(self.calibration_file, "r") as f: return json.load(f)
            except: return {}
        return {}

    def update_pattern_list(self):
        if not os.path.exists("padroes"): os.makedirs("padroes")
        self.pattern_files = [f for f in os.listdir("padroes") if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    def listen_hotkeys(self):
        while True:
            try:
                if not self.winfo_exists(): break
                hk = self.combo_hotkey.get().lower()
                if keyboard.is_pressed(hk): 
                    self.after(0, self.toggle_macro)
                    time.sleep(1.0) 
            except: break
            time.sleep(0.05)

    def toggle_macro(self):
        self.running = not self.running
        color = "#28a745" if self.running else "#ff4444"
        txt = "STATUS: RODANDO" if self.running else "STATUS: PARADO"
        self.status_label.configure(text=txt, text_color=color)
        if self.hud_active and hasattr(self, 'hud_status_label') and self.hud_status_label.winfo_exists():
            self.hud_status_label.configure(text=txt, text_color=color)
        if self.running: threading.Thread(target=self.macro_loop, daemon=True).start()

# --- EXECUÇÃO ---
if __name__ == "__main__":
    try:
        login = LoginWindow()
        login.mainloop()
    except KeyboardInterrupt:
        os._exit(0)