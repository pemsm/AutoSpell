import tkinter as tk
from PIL import Image, ImageTk
import json
import os

class PatternEditor(tk.Frame):
    def __init__(self, parent, pattern_folder="padroes"):
        super().__init__(parent)
        self.pattern_folder = pattern_folder
        self.points_data = {} # Agora armazena o dicionário completo
        self.current_pattern = None
        
        # Constantes de escala para manter compatibilidade com a tela do jogo
        self.CANVAS_W = 960  # Metade da tela (ROI)
        self.CANVAS_H = 1080
        
        # Interface básica
        self.canvas = tk.Canvas(self, width=self.CANVAS_W, height=self.CANVAS_H, bg="black")
        self.canvas.pack(side="left", padx=10, pady=10)
        
        self.canvas.bind("<Button-1>", self.add_point)
        self.canvas.bind("<Button-3>", self.remove_point)
        
        self.load_data()

    def load_pattern(self, pattern_name):
        """Carrega a imagem do padrão e ajusta as coordenadas."""
        self.current_pattern = pattern_name
        # Tenta carregar com ou sem extensão para evitar erros
        img_path = os.path.join(self.pattern_folder, pattern_name)
        if not os.path.exists(img_path):
            img_path = os.path.join(self.pattern_folder, f"{pattern_name}.png")

        if os.path.exists(img_path):
            img = Image.open(img_path).convert("RGBA")
            # Opacidade 0.3 para ver os pontos por cima
            alpha = img.split()[3].point(lambda p: p * 0.3)
            img.putalpha(alpha)
            
            # Redimensiona para o tamanho real da ROI do jogo
            img = img.resize((self.CANVAS_W, self.CANVAS_H))
            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.delete("bg")
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img, tags="bg")
            self.redraw()

    def add_point(self, event):
        if self.current_pattern:
            if self.current_pattern not in self.points_data:
                self.points_data[self.current_pattern] = {"points": []}
            
            # Salva no novo formato de dicionário
            novo_ponto = {
                "x": int(event.x),
                "y": int(event.y),
                "wait": 0.02, # Tempo padrão para cliques manuais
                "key": None
            }
            self.points_data[self.current_pattern]["points"].append(novo_ponto)
            self.redraw()

    def remove_point(self, event):
        if self.current_pattern in self.points_data:
            pts = self.points_data[self.current_pattern]["points"]
            if pts:
                pts.pop()
                self.redraw()

    def redraw(self):
        self.canvas.delete("overlay")
        config = self.points_data.get(self.current_pattern, {})
        pts = config.get("points", [])
        
        for i, p in enumerate(pts):
            # Suporte tanto para formato antigo [x,y] quanto novo {"x":x, "y":y}
            x, y = (p[0], p[1]) if isinstance(p, list) else (p["x"], p["y"])
            
            # Cor diferenciada para o primeiro ponto (âncora)
            cor = "red" if i == 0 else "green"
            
            self.canvas.create_oval(x-4, y-4, x+4, y+4, fill=cor, outline="white", tags="overlay")
            self.canvas.create_text(x+10, y-10, text=str(i+1), fill="yellow", tags="overlay")
            
            if i > 0:
                p_prev = pts[i-1]
                px, py = (p_prev[0], p_prev[1]) if isinstance(p_prev, list) else (p_prev["x"], p_prev["y"])
                self.canvas.create_line(px, py, x, y, fill="cyan", width=1, tags="overlay")

    def save_data(self):
        """Salva preservando o formato que o Vision Engine entende."""
        with open("coordenadas_calibradas.json", "w", encoding='utf-8') as f:
            json.dump(self.points_data, f, indent=4)

    def load_data(self):
        if os.path.exists("coordenadas_calibradas.json"):
            try:
                with open("coordenadas_calibradas.json", "r", encoding='utf-8') as f:
                    self.points_data = json.load(f)
            except:
                self.points_data = {}