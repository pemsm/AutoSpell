import os

def list_files(startpath):
    ignore_list = {'.venv311', 'venv', '__pycache__', '.git', '.env'}
    
    print(f"--- ESTRUTURA ATUAL DO AUTOSPELL ---\n")
    
    for root, dirs, files in os.walk(startpath):
        # Remove pastas ignoradas da varredura
        dirs[:] = [d for d in dirs if d not in ignore_list]
        
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}📂 {os.path.basename(root)}/")
        
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            # Mostra apenas o que é relevante para o código
            if f.endswith(('.py', '.json', '.txt')) and f != 'debug_log.txt':
                print(f"{sub_indent}📜 {f}")

if __name__ == "__main__":
    list_files(os.getcwd())