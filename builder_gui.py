import customtkinter as ctk
import os
import threading
import subprocess
import re
import shutil
import time

class AutoSpellBuilder(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AutoSpell - Deployment Hub")
        self.geometry("600x720")
        ctk.set_appearance_mode("dark")

        # UI Elements
        self.label = ctk.CTkLabel(self, text="AutoSpell Release Manager", font=("Arial", 22, "bold"))
        self.label.pack(pady=(20, 10))

        self.version = self.get_version()
        self.version_label = ctk.CTkLabel(self, text=f"Versão detectada: v{self.version}", text_color="#3b8ed0")
        self.version_label.pack(pady=5)

        # --- SEÇÃO DE PROGRESSO ---
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Pronto para iniciar", font=("Arial", 12))
        self.progress_label.pack(anchor="w")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, progress_color="#47d147", fg_color="#2b2b2b")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10, fill="x")

        self.time_label = ctk.CTkLabel(self.progress_frame, text="Decorrido: 00:00 | Restante: --:--", font=("Consolas", 11))
        self.time_label.pack(anchor="e")

        # Console de Saída
        self.console = ctk.CTkTextbox(self, width=550, height=220, font=("Consolas", 11))
        self.console.pack(pady=20, padx=20)

        # Botão Gerar Release
        self.btn_build = ctk.CTkButton(self, text="GERAR NOVA RELEASE", 
                                      command=self.start_build_thread,
                                      fg_color="#1f538d", hover_color="#14375e", 
                                      height=45, width=410, font=("Arial", 14, "bold"))
        self.btn_build.pack(pady=10)

        # Utilitários
        self.util_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.util_frame.pack(pady=5)

        self.btn_open_folder = ctk.CTkButton(self.util_frame, text="ABRIR PASTA DA RELEASE", 
                                            command=self.open_dist,
                                            state="disabled", fg_color="transparent", border_width=1, width=200)
        self.btn_open_folder.grid(row=0, column=0, padx=5)

        self.btn_clean = ctk.CTkButton(self.util_frame, text="LIMPAR AMBIENTE", 
                                      command=self.manual_clean,
                                      fg_color="#4a4a4a", hover_color="#632d2d", width=200)
        self.btn_clean.grid(row=0, column=1, padx=5)

        self.status_bar = ctk.CTkLabel(self, text="Status: IDLE", text_color="gray")
        self.status_bar.pack(side="bottom", pady=10)

        # Controle de Estado
        self.is_running = False
        self.current_progress = 0
        self.estimated_time = 45 
        self.check_dist_exists()

    def get_version(self):
        try:
            # Versão agora é buscada no novo arquivo principal autospell.py
            if os.path.exists("autospell.py"):
                with open("autospell.py", "r", encoding="utf-8") as f:
                    content = f.read()
                    match = re.search(r'VERSAO_LOCAL\s*=\s*["\']([^"\']+)["\']', content)
                    return match.group(1) if match else "1.0.0"
        except: pass
        return "1.0.0"

    def log(self, message):
        self.console.insert("end", f"> {message}\n")
        self.console.see("end")

    def check_dist_exists(self):
        dist_path = os.path.join(os.getcwd(), "dist")
        if os.path.exists(dist_path) and any(item.endswith('.exe') for item in os.listdir(dist_path)):
            self.btn_open_folder.configure(state="normal", border_color="#3b8ed0", text_color="white")
            return True
        return False

    def smooth_progress_loop(self):
        if not self.is_running: return
        step = 0.0012 
        if self.current_progress < 0.98:
            self.current_progress += step
        self.progress_bar.set(self.current_progress)
        self.after(50, self.smooth_progress_loop)

    def update_timer_ui(self):
        if not self.is_running: return
        elapsed = int(time.time() - self.start_time)
        rem = max(0, self.estimated_time - elapsed)
        elapsed_str = time.strftime('%M:%S', time.gmtime(elapsed))
        rem_str = "Finalizando..." if rem <= 0 else f"Restante: ~{time.strftime('%M:%S', time.gmtime(rem))}"
        self.time_label.configure(text=f"Decorrido: {elapsed_str} | {rem_str}")
        self.after(1000, self.update_timer_ui)

    def manual_clean(self):
        self.log("Limpando ambiente...")
        for folder in ["dist", "build", "obfuscated"]:
            shutil.rmtree(os.path.join(os.getcwd(), folder), ignore_errors=True)
        self.log("✅ Limpeza completa.")
        self.progress_bar.set(0)

    def open_dist(self):
        dist_path = os.path.join(os.getcwd(), "dist")
        if os.path.exists(dist_path): os.startfile(dist_path)

    def start_build_thread(self):
        self.is_running = True
        self.start_time = time.time()
        self.current_progress = 0
        self.btn_build.configure(state="disabled")
        self.console.delete("1.0", "end")
        
        # MOSTRAR barra de progresso
        self.progress_frame.pack(before=self.console, pady=10, padx=30, fill="x")
        
        self.smooth_progress_loop()
        self.update_timer_ui()
        threading.Thread(target=self.run_pipeline, daemon=True).start()

    def run_pipeline(self):
        try:
            curr_dir = os.getcwd()
            version = self.get_version()
            
            # 1. Limpeza
            self.progress_label.configure(text="Etapa 1/3: Preparando ambiente...")
            for f in ["dist", "build", "obfuscated"]:
                shutil.rmtree(os.path.join(curr_dir, f), ignore_errors=True)

            # 2. PyArmor (Ofuscação do novo ponto de entrada)
            self.log("Iniciando ofuscação (PyArmor)...")
            self.progress_label.configure(text="Etapa 2/3: Protegendo código...")
            out_pyarmor = os.path.join(curr_dir, "obfuscated")
            
            # Alterado para autospell.py
            res_pa = subprocess.run(f'pyarmor gen --output "{out_pyarmor}" "autospell.py"', 
                                    shell=True, capture_output=True, text=True)
            if res_pa.returncode != 0: raise Exception(f"PyArmor falhou: {res_pa.stderr}")

            # 3. PyInstaller (Criação do Executável)
            self.log("Iniciando empacotamento (PyInstaller)...")
            self.progress_label.configure(text="Etapa 3/3: Criando executável...")
            
            exe_name = f"AutoSpell_v{version}"
            script_src = os.path.join(out_pyarmor, "autospell.py") # Uso do arquivo ofuscado
            
            cmd_pyi = [
                "pyinstaller", "--noconfirm", "--onefile", "--windowed",
                f'--name "{exe_name}"',
                "--clean",
                f'--paths "{out_pyarmor}"', 
                f'--paths "{curr_dir}"', 
                "--collect-all customtkinter",
                "--hidden-import PIL.ImageResampling",
                "--hidden-import core.vision_engine",
                "--hidden-import core.pattern_analyzer",
                "--hidden-import ui.main_app",
                "--hidden-import ui.login_window",
                "--hidden-import ui.pattern_editor",
                "--hidden-import utils.config_manager",
                "--hidden-import utils.logger",
                # Mapeamento de pastas para garantir que recursos (PNGs) sejam incluídos
                f'--add-data "ui;ui"',
                f'--add-data "core;core"',
                f'--add-data "utils;utils"',
                f'--add-data "data;data"',
                f'--add-data "padroes;padroes"',
                f'"{script_src}"'
            ]
            
            res_pyi = subprocess.run(" ".join(cmd_pyi), shell=True, capture_output=True, text=True)
            if res_pyi.returncode != 0: raise Exception(f"PyInstaller falhou: {res_pyi.stderr}")

            # Conclusão
            self.current_progress = 1.0
            self.progress_bar.set(1.0)
            
            if self.check_dist_exists():
                self.log(f"✅ Build concluído: {exe_name}.exe")
                self.progress_label.configure(text="✅ Tudo pronto!")
                self.status_bar.configure(text="Release disponível!", text_color="#47d147")
            else:
                raise Exception("Executável não foi gerado na pasta dist.")
            
        except Exception as e:
            self.log(f"❌ ERRO: {str(e)}")
            self.status_bar.configure(text="Erro no build", text_color="#ff4d4d")
        finally:
            self.is_running = False
            self.btn_build.configure(state="normal")

if __name__ == "__main__":
    app = AutoSpellBuilder()
    app.mainloop()