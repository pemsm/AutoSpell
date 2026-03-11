import customtkinter as ctk
import threading
import time
import keyboard
import pyautogui
import os
import json
import logging
from PIL import Image, ImageTk
from vision_engine import run_macro

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    filename='debug_log.txt',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

SCREEN_W = 1920
SCREEN_H = 1080
ROI_OFFSET_X = 960 
SAMPLING_RATE = 0.01

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wizard HUD - Ghost Edition")
        self.geometry("950x850") 
        self.attributes("-topmost", True)
        
        self.running = False
        self.hud_active = False
        self.full_calib_active = False
        self.recording = False
        self.is_playing_preview = False
        self.show_points_active = False 
        self.tk_img = None 
        
        self.calibration_file = "coordenadas_calibradas.json"
        self.points_data = self.load_calibration()
        self.current_editing_pattern = None
        self.temp_points = [] 
        self.stats = {"sucessos": 0, "fracassos": 0, "total": 0}

        # --- UI SETUP ---
        self.tabview = ctk.CTkTabview(self, width=930, height=800)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.tab_main = self.tabview.add("Automação")
        self.tab_calibrate = self.tabview.add("Gravar Movimento")

        self.setup_main_tab()
        self.setup_calibrate_tab()

        # Usando hotkeys registradas (mais leves que loops de while True)
        keyboard.add_hotkey('f6', self.trigger_f6)
        keyboard.add_hotkey('f7', self.trigger_f7)
        keyboard.add_hotkey('f9', self.trigger_f9)
        
        threading.Thread(target=self.listen_hotkeys, daemon=True).start()

    def setup_main_tab(self):
        self.status_label = ctk.CTkLabel(self.tab_main, text="AGUARDANDO START (F5)", font=("Arial", 24, "bold"), text_color="#555")
        self.status_label.pack(pady=(20, 10))

        self.stats_frame = ctk.CTkFrame(self.tab_main, fg_color="#1a1a1a", corner_radius=10)
        self.stats_frame.pack(pady=10, padx=20, fill="x")
        
        self.lbl_suc = ctk.CTkLabel(self.stats_frame, text="✅ Sucessos: 0", font=("Arial", 16), text_color="#2ecc71")
        self.lbl_suc.pack(side="left", expand=True, pady=10)
        
        self.lbl_fail = ctk.CTkLabel(self.stats_frame, text="❌ Falhas: 0", font=("Arial", 16), text_color="#e74c3c")
        self.lbl_fail.pack(side="left", expand=True, pady=10)

        self.lbl_total = ctk.CTkLabel(self.stats_frame, text="📊 Total: 0", font=("Arial", 16), text_color="#3498db")
        self.lbl_total.pack(side="left", expand=True, pady=10)

        self.frame_inputs = ctk.CTkFrame(self.tab_main)
        self.frame_inputs.pack(pady=10, padx=20, fill="x")

        self.teclas_disponiveis = [f"f{i}" for i in range(1, 13)]
        
        ctk.CTkLabel(self.frame_inputs, text="Console:").grid(row=0, column=0, padx=10, pady=5)
        self.combo_tecla_console = ctk.CTkComboBox(self.frame_inputs, values=self.teclas_disponiveis, width=100)
        self.combo_tecla_console.set("f8")
        self.combo_tecla_console.grid(row=0, column=1, padx=10)

        ctk.CTkLabel(self.frame_inputs, text="ON/OFF:").grid(row=0, column=2, padx=10, pady=5)
        self.combo_hotkey = ctk.CTkComboBox(self.frame_inputs, values=self.teclas_disponiveis, width=100)
        self.combo_hotkey.set("f5")
        self.combo_hotkey.grid(row=0, column=3, padx=10)

        self.entry_comando = ctk.CTkEntry(self.tab_main, placeholder_text="Comando (ex: m11)", width=400, height=40)
        self.entry_comando.insert(0, "m11")
        self.entry_comando.pack(pady=20)

        self.btn_hud = ctk.CTkButton(self.tab_main, text="ATIVAR MODO HUD COMPACTO", fg_color="#1f538d", height=45, command=self.toggle_hud_mode)
        self.btn_hud.pack(pady=10)

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

        self.btn_save = ctk.CTkButton(self.ctrl_panel, text="💾 SALVAR", fg_color="#27ae60", command=self.save_calibration)
        self.btn_save.pack(pady=5)

        self.btn_preview = ctk.CTkButton(self.ctrl_panel, text="👁 VER RASTRO", fg_color="#555", command=self.toggle_preview_visuals)
        self.btn_preview.pack(pady=5)
        
        self.btn_full_calib = ctk.CTkButton(self.ctrl_panel, text="🖥 MODO HUD GRAVAÇÃO (F9)", fg_color="#d35400", command=self.toggle_full_calibration)
        self.btn_full_calib.pack(pady=5)

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
        self.recording = True
        self.temp_points = []
        self.canvas.delete("pt")
        self.update_rec_label("● GRAVANDO...", "#FF4444")
        threading.Thread(target=self.record_loop, daemon=True).start()

    def stop_recording(self):
        self.recording = False
        self.update_rec_label("✅ GRAVADO COM SUCESSO!", "#00FF00")
        self.show_points_active = True
        self.btn_preview.configure(text="❌ OCULTAR PREVIEWS", fg_color="#e74c3c")
        self.redraw_canvas()
        self.start_ghost_preview()

    def toggle_preview_visuals(self):
        if not self.temp_points: return
        self.show_points_active = not self.show_points_active
        if self.show_points_active:
            self.btn_preview.configure(text="❌ OCULTAR PREVIEWS", fg_color="#e74c3c")
            self.redraw_canvas()
            self.start_ghost_preview()
        else:
            self.btn_preview.configure(text="👁 VER RASTRO", fg_color="#555")
            self.canvas.delete("pt", "ghost")

    def update_rec_label(self, texto, cor):
        # Só tenta atualizar se o atributo existir e o widget estiver vivo
        if hasattr(self, 'hud_rec_status') and self.hud_rec_status.winfo_exists():
            self.hud_rec_status.configure(text=texto, text_color=cor)
        else:
            # Caso não esteja no HUD, loga no console ou atualiza o status da aba
            self.lbl_rec_status.configure(text=texto, text_color=cor)
            logging.info(f"Status Rec: {texto}")

    def record_loop(self):
        last_check = time.time()
        teclas_monitoradas = ['c', 'x', 'z']
        
        while self.recording:
            agora = time.time()
            if agora - last_check >= SAMPLING_RATE:
                x, y = pyautogui.position()
                dt = round(agora - last_check, 4)
                
                tecla_pressionada = None
                for t in teclas_monitoradas:
                    if keyboard.is_pressed(t):
                        tecla_pressionada = t
                        break 
                
                self.temp_points.append({
                    "x": int(x - ROI_OFFSET_X), 
                    "y": int(y), 
                    "wait": dt,
                    "key": tecla_pressionada
                })
                
                last_check = agora
                # Importante: redraw_canvas agora deve usar o canvas_hud se estiver ativo
                self.after(0, self.redraw_canvas)
            time.sleep(0.001)

    def redraw_canvas(self):
        self.canvas.delete("pt")
        if not self.temp_points or not self.show_points_active: return
        
        # Desenho em lote para evitar lag
        for p in self.temp_points:
            # Compatibilidade Lista vs Dicionário
            if isinstance(p, list):
                dx, dy = p[0] + ROI_OFFSET_X, p[1]
            else:
                dx, dy = p.get("x", 0) + ROI_OFFSET_X, p.get("y", 0)
            
            self.canvas.create_oval(dx-1, dy-1, dx+1, dy+1, fill="#00FFFF", outline="", tags="pt")

    def start_ghost_preview(self):
        if not self.temp_points or self.is_playing_preview: return
        threading.Thread(target=self.ghost_playback_thread, daemon=True).start()

    def ghost_playback_thread(self):
        self.is_playing_preview = True
        ghost = self.canvas.create_oval(0,0,0,0, fill="#00FF00", outline="white", width=2, tags="ghost")
        for p in self.temp_points:
            if not self.show_points_active: break
            
            if isinstance(p, list):
                dx, dy, wait = p[0] + ROI_OFFSET_X, p[1], 0.01
            else:
                dx, dy, wait = p.get("x", 0) + ROI_OFFSET_X, p.get("y", 0), p.get("wait", 0.01)

            self.canvas.coords(ghost, dx-6, dy-6, dx+6, dy+6)
            self.canvas.tag_raise("ghost")
            time.sleep(wait)
        self.canvas.delete("ghost")
        self.is_playing_preview = False

    def toggle_full_calibration(self):
        self.full_calib_active = not self.full_calib_active
        
        if self.full_calib_active:
            # Esconde a janela principal para não atrapalhar a visão do jogo
            self.withdraw() 
            
            # Cria uma janela de HUD dedicada para gravação (Overlay)
            self.hud_window = ctk.CTkToplevel(self)
            self.hud_window.geometry(f"{SCREEN_W}x{SCREEN_H}+0+0")
            self.hud_window.overrideredirect(True)
            self.hud_window.attributes("-topmost", True)
            self.hud_window.attributes("-transparentcolor", "black")
            self.hud_window.config(bg="black")
            
            # Label de status dentro dessa nova janela
            self.hud_rec_status = ctk.CTkLabel(
                self.hud_window, 
                text="MODO GRAVAÇÃO: F6 para Iniciar | F7 para Parar", 
                font=("Arial", 20, "bold"),
                text_color="yellow"
            )
            self.hud_rec_status.pack(pady=50)
            
            # Canvas de desenho (agora filho da hud_window)
            self.canvas_hud = ctk.CTkCanvas(
                self.hud_window, width=SCREEN_W, height=SCREEN_H, 
                bg="black", highlightthickness=0
            )
            self.canvas_hud.pack()
            
        else:
            if hasattr(self, 'hud_window'):
                self.hud_window.destroy()
            self.deiconify() # Volta com a janela principal

    def load_pattern_to_canvas(self, filename):
        self.current_editing_pattern = filename
        path = os.path.join("padroes", filename)
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            # Processamento otimizado de transparência
            alpha = img.getchannel('A')
            alpha = alpha.point(lambda i: i * 0.4)
            img.putalpha(alpha)
            
            img = img.resize((SCREEN_W - ROI_OFFSET_X, SCREEN_H))
            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.delete("bg")
            self.canvas.create_image(ROI_OFFSET_X, 0, anchor="nw", image=self.tk_img, tags="bg")
        
        data_json = self.points_data.get(filename, {})
        self.temp_points = data_json.get("points", [])
        self.show_points_active = False
        self.btn_preview.configure(text="👁 VER RASTRO", fg_color="#555")
        self.canvas.delete("pt", "ghost")

        if self.temp_points:
            self.update_rec_label("✅ GRAVADO COM SUCESSO!", "#00FF00")
        else:
            self.update_rec_label("F6: Rec | F7: Stop | F9: Modo HUD", "white")

    def toggle_hud_mode(self):
        if not self.hud_active:
            self.hud_active = True
            self.geometry("400x250+10+10") 
            self.attributes("-alpha", 0.8)
            self.tabview.pack_forget()
            self.hud_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
            self.hud_frame.pack(fill="both", expand=True)
            ctk.CTkLabel(self.hud_frame, text="WIZARD HUD", font=("Arial", 14, "bold"), text_color="#00FFFF").pack(pady=5)
            self.hud_status_label = ctk.CTkLabel(self.hud_frame, text=self.status_label.cget("text"), font=("Arial", 16, "bold"))
            self.hud_status_label.pack(pady=10)
            ctk.CTkButton(self.hud_frame, text="VOLTAR (MENU)", height=25, command=self.toggle_hud_mode).pack(pady=10)
        else:
            self.hud_active = False
            self.attributes("-alpha", 1.0)
            self.geometry("950x850")
            if hasattr(self, 'hud_frame'): self.hud_frame.destroy()
            self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

    def update_stats(self, tipo):
        self.stats[tipo] += 1
        self.stats["total"] += 1
        self.lbl_suc.configure(text=f"✅ Sucessos: {self.stats['sucessos']}")
        self.lbl_fail.configure(text=f"❌ Falhas: {self.stats['fracassos']}")
        self.lbl_total.configure(text=f"📊 Total: {self.stats['total']}")

    def save_calibration(self):
        if self.current_editing_pattern:
            self.points_data[self.current_editing_pattern] = {"points": self.temp_points}
            with open(self.calibration_file, "w") as f:
                json.dump(self.points_data, f, indent=4)
            self.update_rec_label("✅ DADOS SALVOS!", "#00FF00")

    def load_calibration(self):
        if os.path.exists(self.calibration_file):
            try:
                with open(self.calibration_file, "r") as f: return json.load(f)
            except: return {}
        return {}

    def update_pattern_list(self):
        if not os.path.exists("padroes"): os.makedirs("padroes")
        self.pattern_files = [f for f in os.listdir("padroes") if f.lower().endswith(('.png', '.jpg'))]

    def listen_hotkeys(self):
        while True:
            try:
                hk = self.combo_hotkey.get().lower()
                if keyboard.is_pressed(hk):
                    self.after(0, self.toggle_macro)
                    time.sleep(1.0) # Debounce
            except: pass
            time.sleep(0.05)

    def toggle_macro(self):
        self.running = not self.running
        color = "#28a745" if self.running else "#ff4444"
        txt = "STATUS: RODANDO" if self.running else "STATUS: PARADO"
        self.status_label.configure(text=txt, text_color=color)
        if self.hud_active and hasattr(self, 'hud_status_label'):
            self.hud_status_label.configure(text=txt, text_color=color)
        if self.running:
            threading.Thread(target=self.macro_loop, daemon=True).start()

    def macro_loop(self):
        cmd = self.entry_comando.get()
        console = self.combo_tecla_console.get()
        
        while self.running:
            def dual_status_update(texto, text_color=None):
                self.status_label.configure(text=texto)
                if text_color: self.status_label.configure(text_color=text_color)
                if self.hud_active and hasattr(self, 'hud_status_label'):
                    self.hud_status_label.configure(text=texto)
                    if text_color: self.hud_status_label.configure(text_color=text_color)

            class StatusProxy:
                def configure(self, **kwargs):
                    if "text" in kwargs: 
                        # Usa after para atualizar UI com segurança
                        app.after(0, lambda: dual_status_update(kwargs["text"], kwargs.get("text_color")))
            
            # BLOQUEANTE: O run_macro agora só retorna quando o ciclo de 3s acabar
            run_macro(cmd, StatusProxy(), self.update_stats, console)
            
            if not self.running: break

if __name__ == "__main__":
    app = App()
    app.mainloop()