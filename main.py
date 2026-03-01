import customtkinter as ctk
import threading
import time
import keyboard
import os
import shutil
import json
from PIL import Image, ImageTk
from vision_engine import run_macro
from pattern_analyzer import PatternAnalyzer

# Configurações de Resolução Nativa
SCREEN_W = 1920
SCREEN_H = 1080

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wizard Auto-Cast PRO")
        # Iniciamos com tamanho padrão, mas a aba de calibração usará o espaço total
        self.geometry("900x700") 
        self.running = False
        
        # Dados de Calibração
        self.calibration_file = "coordenadas_calibradas.json"
        self.points_data = self.load_calibration()
        self.current_editing_pattern = None
        self.temp_points = []

        # Motores
        self.stats = {"sucessos": 0, "fracassos": 0, "reinicios": 0}
        self.analyzer = PatternAnalyzer()

        # --- ESTRUTURA DE ABAS ---
        self.tabview = ctk.CTkTabview(self, width=880, height=650)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.tab_main = self.tabview.add("Automação")
        self.tab_config = self.tabview.add("Analisador")
        self.tab_calibrate = self.tabview.add("Calibrar Padrões")

        self.setup_main_tab()
        self.setup_config_tab()
        self.setup_calibrate_tab()

        # Escuta de hotkeys
        threading.Thread(target=self.listen_hotkeys, daemon=True).start()

    def setup_main_tab(self):
        self.status_label = ctk.CTkLabel(self.tab_main, text="Status: Aguardando...", font=("Arial", 22, "bold"))
        self.status_label.pack(pady=20)

        frame_inputs = ctk.CTkFrame(self.tab_main)
        frame_inputs.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(frame_inputs, text="Tecla Console:").grid(row=0, column=0, padx=10, pady=5)
        self.teclas_disponiveis = [f"f{i}" for i in range(1, 13)]
        self.combo_tecla_console = ctk.CTkComboBox(frame_inputs, values=self.teclas_disponiveis, width=120)
        self.combo_tecla_console.set("f8")
        self.combo_tecla_console.grid(row=0, column=1, padx=10)

        ctk.CTkLabel(frame_inputs, text="Hotkey ON/OFF:").grid(row=0, column=2, padx=10, pady=5)
        self.combo_hotkey = ctk.CTkComboBox(frame_inputs, values=self.teclas_disponiveis, width=120)
        self.combo_hotkey.set("f10")
        self.combo_hotkey.grid(row=0, column=3, padx=10)

        self.entry_comando = ctk.CTkEntry(self.tab_main, placeholder_text="Comando do feitiço...", width=400)
        self.entry_comando.insert(0, "magia aresto")
        self.entry_comando.pack(pady=20)

        self.stats_frame = ctk.CTkFrame(self.tab_main)
        self.stats_frame.pack(pady=10, padx=20, fill="x")
        self.lbl_sucessos = ctk.CTkLabel(self.stats_frame, text="✅ Sucessos: 0", text_color="#28a745", font=("Arial", 14, "bold"))
        self.lbl_sucessos.pack(side="left", expand=True, pady=15)
        self.lbl_fracassos = ctk.CTkLabel(self.stats_frame, text="❌ Falhas: 0", text_color="#dc3545", font=("Arial", 14, "bold"))
        self.lbl_fracassos.pack(side="left", expand=True, pady=15)

    def setup_config_tab(self):
        ctk.CTkLabel(self.tab_config, text="Analisador de Imagens", font=("Arial", 18, "bold")).pack(pady=15)
        self.btn_analisar = ctk.CTkButton(self.tab_config, text="🔍 GERAR OVERLAYS", command=self.run_pattern_analysis)
        self.btn_analisar.pack(pady=10)
        self.btn_abrir = ctk.CTkButton(self.tab_config, text="📁 VER RESULTADOS", fg_color="#333", command=self.open_output_folder)
        self.btn_abrir.pack(pady=10)

    # --- ABA 3: CALIBRAR (MODO FULL PRECISION) ---
    def setup_calibrate_tab(self):
        # Canvas ocupando todo o espaço disponível para precisão 1920x1080
        self.canvas = ctk.CTkCanvas(self.tab_calibrate, width=SCREEN_W, height=SCREEN_H, bg="#050505", highlightthickness=0)
        self.canvas.place(x=0, y=0)
        
        self.canvas.bind("<Button-1>", self.add_calibration_point)
        self.canvas.bind("<Button-3>", self.remove_last_point)

        # Painel de Controle Flutuante (Canto inferior esquerdo)
        self.ctrl_panel = ctk.CTkFrame(self.tab_calibrate, fg_color=("#2b2b2b", "#1a1a1a"), corner_radius=10, border_width=2)
        self.ctrl_panel.place(relx=0.02, rely=0.65, relwidth=0.25, relheight=0.3)

        ctk.CTkLabel(self.ctrl_panel, text="CALIBRAÇÃO 1:1", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.update_pattern_list()
        self.combo_patterns = ctk.CTkComboBox(self.ctrl_panel, values=self.pattern_files, command=self.load_pattern_to_canvas)
        self.combo_patterns.pack(pady=5, padx=10)

        ctk.CTkLabel(self.ctrl_panel, text="Tempo (ms):", font=("Arial", 10)).pack()
        self.speed_slider = ctk.CTkSlider(self.ctrl_panel, from_=100, to=5000, number_of_steps=49)
        self.speed_slider.set(1000)
        self.speed_slider.pack(pady=2, padx=10)

        btn_row = ctk.CTkFrame(self.ctrl_panel, fg_color="transparent")
        btn_row.pack(pady=10)
        
        ctk.CTkButton(btn_row, text="💾 SALVAR", width=80, fg_color="#1f538d", command=self.save_calibration).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="🗑️ LIMPAR", width=80, fg_color="#555", command=self.clear_current_points).pack(side="left", padx=5)

    def update_pattern_list(self):
        if not os.path.exists("padroes"): os.makedirs("padroes")
        self.pattern_files = [f for f in os.listdir("padroes") if f.lower().endswith(('.png', '.jpg'))]

    def load_pattern_to_canvas(self, filename):
        self.current_editing_pattern = filename
        path = os.path.join("padroes", filename)
        
        # Carrega imagem original 1920x1080
        img = Image.open(path).convert("RGBA")
        # Aplica transparência para facilitar a visão dos pontos
        alpha = img.split()[3]
        alpha = alpha.point(lambda p: p * 0.5) 
        img.putalpha(alpha)
        
        # Garante que a imagem esteja no tamanho real da tela
        img = img.resize((SCREEN_W, SCREEN_H))
        self.tk_img = ImageTk.PhotoImage(img)
        
        self.canvas.delete("bg")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img, tags="bg")
        
        # Carrega dados salvos
        data = self.points_data.get(filename, {})
        self.temp_points = data.get("points", [])
        self.speed_slider.set(data.get("duration_ms", 1000))
        self.redraw_canvas()

    def add_calibration_point(self, event):
        if not self.current_editing_pattern: return
        # Salva a coordenada EXATA do clique (X, Y)
        self.temp_points.append((event.x, event.y))
        self.redraw_canvas()

    def redraw_canvas(self):
        self.canvas.delete("pt")
        for i, (x, y) in enumerate(self.temp_points):
            color = "#00FF00" if i == 0 else "#FFFF00"
            # Círculo maior para facilitar visualização no 1080p
            self.canvas.create_oval(x-6, y-6, x+6, y+6, fill=color, outline="black", tags="pt")
            if i > 0:
                prev_x, prev_y = self.temp_points[i-1]
                self.canvas.create_line(prev_x, prev_y, x, y, fill="#00FFFF", width=3, tags="pt")
            self.canvas.create_text(x+15, y-15, text=str(i+1), fill="white", font=("Arial", 10, "bold"), tags="pt")

    def save_calibration(self):
        if not self.current_editing_pattern: return
        self.points_data[self.current_editing_pattern] = {
            "points": self.temp_points,
            "duration_ms": self.speed_slider.get()
        }
        with open(self.calibration_file, "w") as f:
            json.dump(self.points_data, f, indent=4)
        print(f"Salvo com precisão nativa: {self.current_editing_pattern}")

    def load_calibration(self):
        if os.path.exists(self.calibration_file):
            with open(self.calibration_file, "r") as f:
                return json.load(f)
        return {}

    # --- RESTANTE DA LÓGICA ---
    def remove_last_point(self, event):
        if self.temp_points:
            self.temp_points.pop()
            self.redraw_canvas()

    def clear_current_points(self):
        self.temp_points = []
        self.redraw_canvas()

    def run_pattern_analysis(self):
        output_path = "padroes_conferidos"
        if os.path.exists(output_path): shutil.rmtree(output_path)
        os.makedirs(output_path)
        try:
            self.analyzer.process_all()
        except Exception as e:
            print(f"Erro: {e}")

    def open_output_folder(self):
        path = os.path.abspath("padroes_conferidos")
        os.startfile(path)

    def update_stats(self, tipo):
        if tipo in self.stats:
            self.stats[tipo] += 1
            self.lbl_sucessos.configure(text=f"✅ Sucessos: {self.stats['sucessos']}")
            self.lbl_fracassos.configure(text=f"❌ Falhas: {self.stats['fracassos']}")

    def listen_hotkeys(self):
        while True:
            try:
                hk = self.combo_hotkey.get().lower()
                if keyboard.is_pressed(hk):
                    self.toggle_macro()
                    time.sleep(1)
            except: pass
            time.sleep(0.05)

    def toggle_macro(self):
        if not self.running:
            cmd = self.entry_comando.get()
            console = self.combo_tecla_console.get()
            if not cmd: return
            self.running = True
            self.status_label.configure(text="Status: RODANDO", text_color="#28a745")
            threading.Thread(target=self.macro_loop, args=(cmd, console), daemon=True).start()
        else:
            self.running = False
            self.status_label.configure(text="Status: INTERROMPIDO", text_color="#ff4444")

    def macro_loop(self, cmd, console):
        while self.running:
            run_macro(cmd, self.status_label, self.update_stats, console)
            for _ in range(20): 
                if not self.running: break
                time.sleep(0.1)

if __name__ == "__main__":
    app = App()
    app.mainloop()