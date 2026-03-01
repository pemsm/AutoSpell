import tkinter as tk
from PIL import Image, ImageTk
import json
import os

class PatternEditor(tk.Frame):
    def __init__(self, parent, pattern_folder="padroes"):
        super().__init__(parent)
        self.pattern_folder = pattern_folder
        self.points = {} # Armazena { "nome_padrao": [(x, y), (x, y)] }
        self.current_pattern = None
        self.load_data()
        
        # Canvas para desenhar
        self.canvas = tk.Canvas(self, width=680, height=680, bg="black")
        self.canvas.pack(side="left", padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.add_point)
        self.canvas.bind("<Button-3>", self.remove_point)

    def load_pattern(self, pattern_name):
        self.current_pattern = pattern_name
        img_path = os.path.join(self.pattern_folder, f"{pattern_name}.png")
        
        if os.path.exists(img_path):
            # Carrega a imagem e aplica transparência (opacidade 0.3)
            img = Image.open(img_path).convert("RGBA")
            alpha = img.split()[3]
            alpha = alpha.point(lambda p: p * 0.3)
            img.putalpha(alpha)
            
            # Ajusta ao tamanho do Canvas
            img = img.resize((680, 680))
            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
            self.redraw()

    def add_point(self, event):
        if self.current_pattern:
            if self.current_pattern not in self.points:
                self.points[self.current_pattern] = []
            self.points[self.current_pattern].append((event.x, event.y))
            self.redraw()

    def remove_point(self, event):
        if self.current_pattern in self.points and self.points[self.current_pattern]:
            self.points[self.current_pattern].pop()
            self.redraw()

    def redraw(self):
        # Limpa apenas os desenhos (pontos e linhas), mantém o fundo
        self.canvas.delete("overlay")
        pts = self.points.get(self.current_pattern, [])
        
        for i, (x, y) in enumerate(pts):
            # Desenha o ponto
            self.canvas.create_oval(x-5, y-5, x+5, y+5, fill="green", outline="white", tags="overlay")
            # Número do ponto
            self.canvas.create_text(x+12, y-12, text=str(i+1), fill="yellow", font=("Arial", 10, "bold"), tags="overlay")
            # Linha ligando ao ponto anterior
            if i > 0:
                prev_x, prev_y = pts[i-1]
                self.canvas.create_line(prev_x, prev_y, x, y, fill="cyan", width=2, tags="overlay")

    def save_data(self):
        with open("coordenadas_calibradas.json", "w") as f:
            json.dump(self.points, f)

    def load_data(self):
        if os.path.exists("coordenadas_calibradas.json"):
            with open("coordenadas_calibradas.json", "r") as f:
                self.points = json.load(f)