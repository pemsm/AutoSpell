import cv2
import numpy as np
import os
import shutil

class PatternAnalyzer:
    def __init__(self, input_folder="padroes", output_folder="padroes_conferidos"):
        self.input_folder = input_folder
        self.output_folder = output_folder

    def get_spell_roi(self, img):
        """Define a área de busca baseada em 1920x1080."""
        h_img, w_img = img.shape[:2]
        x = int(1150 * (w_img / 1920))
        y = int(200 * (h_img / 1080)) # Subi um pouco para pegar o topo da lua
        w = int(680 * (w_img / 1920))
        h = int(680 * (h_img / 1080))
        return x, y, w, h

    def refine_point_by_brightness(self, img, x, y, window=30):
        """
        Ajusta um ponto para o local mais brilhante ao redor dele.
        Evita que o ponto fique no 'vazio' se a coordenada estiver levemente torta.
        """
        roi = img[max(0, y-window):y+window, max(0, x-window):x+window]
        if roi.size == 0: return x, y
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, max_val, _, max_loc = cv2.minMaxLoc(gray)
        if max_val > 100: # Se achou brilho suficiente
            return (x - window + max_loc[0]), (y - window + max_loc[1])
        return x, y

    def get_smart_vertices(self, pattern_name, x_off, y_off, w, h, img):
        """Dicionário com lógica de vértices corrigida e estratégica."""
        # Proporções internas ajustadas para não 'vazar' do desenho
        patterns = {
            "circulo": [(0.5, 0.9), (0.15, 0.5), (0.5, 0.1), (0.85, 0.5), (0.5, 0.9)],
            "triangulo": [(0.2, 0.82), (0.5, 0.15), (0.8, 0.82), (0.2, 0.82)],
            "z": [(0.22, 0.22), (0.78, 0.22), (0.22, 0.78), (0.78, 0.78)],
            "semi_circulo": [(0.15, 0.7), (0.3, 0.25), (0.7, 0.25), (0.85, 0.7)],
            "lua_base": [
                (0.5, 0.1),   # Topo central
                (0.2, 0.35),  # Curva esquerda alta
                (0.2, 0.75),  # Curva esquerda baixa
                (0.8, 0.75),  # Curva direita baixa
                (0.8, 0.35),  # Curva direita alta
                (0.5, 0.1)    # Fecha no topo
            ],
            "minhoca": [(0.1, 0.55), (0.3, 0.25), (0.5, 0.75), (0.7, 0.25), (0.9, 0.55)],
            "semi_curvado": [(0.8, 0.15), (0.2, 0.5), (0.8, 0.85)],
            "semi_quadrado": [(0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75)],
            "semi_triangulo": [(0.2, 0.8), (0.5, 0.2), (0.8, 0.8)]
        }
        
        raw_points = patterns.get(pattern_name, [])
        final_points = []
        
        for px, py in raw_points:
            # Converte para pixel real
            abs_x = int(x_off + px * w)
            abs_y = int(y_off + py * h)
            # Refina: "Puxa" o ponto para a parte mais clara do desenho
            refined_x, refined_y = self.refine_point_by_brightness(img, abs_x, abs_y)
            final_points.append((refined_x, refined_y))
            
        return final_points

    def process_all(self):
        if os.path.exists(self.output_folder):
            shutil.rmtree(self.output_folder)
        os.makedirs(self.output_folder)

        files = [f for f in os.listdir(self.input_folder) if f.lower().endswith(('.png', '.jpg'))]
        
        for file in files:
            img = cv2.imread(os.path.join(self.input_folder, file))
            if img is None: continue
            
            x, y, w, h = self.get_spell_roi(img)
            name = os.path.splitext(file)[0]
            
            # Ghost Overlay
            overlay = cv2.addWeighted(img, 0.2, np.zeros_like(img), 0.8, 0)
            
            # Desenha a ROI (caixa cinza fraca)
            cv2.rectangle(overlay, (x, y), (x+w, y+h), (60, 60, 60), 1)

            vertices = self.get_smart_vertices(name, x, y, w, h, img)
            
            if vertices:
                # Desenha trajetória
                for i in range(len(vertices)-1):
                    cv2.line(overlay, vertices[i], vertices[i+1], (0, 255, 255), 2, cv2.LINE_AA)
                
                # Desenha pontos de impacto
                for i, pt in enumerate(vertices):
                    cv2.circle(overlay, pt, 5, (0, 255, 0), -1)
                    cv2.putText(overlay, str(i+1), (pt[0]+10, pt[1]-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imwrite(os.path.join(self.output_folder, f"analise_{file}"), overlay)