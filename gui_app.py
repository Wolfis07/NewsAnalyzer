import tkinter as tk
from tkinter import ttk, messagebox
import requests
from bs4 import BeautifulSoup
from queue import Queue
from threading import Thread, Lock
import time
import sys

# Importujeme tvou existující třídu Worker
from worker import Worker

# --- Konfigurace (Stejná jako předtím) ---
TARGET_URL = "https://www.theregister.com"
KEYWORDS = ["AI", "Security", "Cloud", "Microsoft", "Linux", "Data", "Cyber", "Chip", "Code"]
NUM_WORKERS = 4
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
}

class NewsAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Paralelní News Analyzer (The Register)")
        self.root.geometry("1000x600")

        # Sdílené zdroje
        self.url_queue = Queue()
        self.results = []
        self.results_lock = Lock()
        self.is_running = False

        # --- Grafické prvky (Layout) ---
        
        # 1. Horní panel s ovládáním
        frame_top = tk.Frame(root, pady=10)
        frame_top.pack(side=tk.TOP, fill=tk.X)

        self.btn_start = tk.Button(frame_top, text="Spustit Analýzu", command=self.start_analysis_thread, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
        self.btn_start.pack(side=tk.LEFT, padx=20)

        self.lbl_status = tk.Label(frame_top, text="Připraveno", font=("Arial", 10))
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        # 2. Tabulka výsledků (Treeview)
        frame_table = tk.Frame(root)
        frame_table.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("score", "status", "title", "url")
        self.tree = ttk.Treeview(frame_table, columns=columns, show="headings")
        
        # Definice sloupců
        self.tree.heading("score", text="Skóre")
        self.tree.column("score", width=50, anchor=tk.CENTER)
        
        self.tree.heading("status", text="Stav")
        self.tree.column("status", width=80, anchor=tk.CENTER)
        
        self.tree.heading("title", text="Titulek Článku")
        self.tree.column("title", width=400)
        
        self.tree.heading("url", text="URL")
        self.tree.column("url", width=300)

        # Scrollbar pro tabulku
        scrollbar = ttk.Scrollbar(frame_table, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

    # --- Logika Aplikace ---

    def analyze_text_score(self, text, keywords):
        """ Stejná funkce jako předtím, jen uvnitř třídy """
        text_lower = text.lower()
        return sum(text_lower.count(k.lower()) for k in keywords)

    def start_analysis_thread(self):
        """ Spustí hlavní proces v novém vlákně, aby nezamrzlo GUI """
        self.btn_start.config(state=tk.DISABLED)
        self.results = [] # Vymazat staré výsledky
        
        # Vymazání tabulky
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.is_running = True
        
        # Spuštění "Manažera" (Producenta) v samostatném vlákně
        manager_thread = Thread(target=self.run_producer_logic)
        manager_thread.start()
        
        # Spuštění pravidelné aktualizace GUI
        self.root.after(100, self.update_gui)

    def run_producer_logic(self):
        """ Toto je kód, který byl dříve v main() """
        self.update_status("Stahování dat z The Register...")
        
        tasks = []
        try:
            response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            potential_articles = soup.find_all(['h3', 'h4', 'article'])
            
            for item in potential_articles:
                link = item.find('a')
                if link and link.get('href'):
                    title = link.text.strip()
                    href = link.get('href')
                    if len(title) < 5: continue
                    
                    if href.startswith('/'): full_url = TARGET_URL + href
                    elif href.startswith('http'): full_url = href
                    else: continue
                    
                    if (title, full_url) not in tasks:
                        tasks.append((title, full_url))
            
            if not tasks:
                self.update_status("Chyba: Nenalezeny žádné články.")
                self.is_running = False
                return

        except Exception as e:
            self.update_status(f"Chyba připojení: {e}")
            self.is_running = False
            return

        self.update_status(f"Nalezeno {len(tasks)} článků. Spouštím {NUM_WORKERS} vláken...")
        
        # Plnění fronty
        for task in tasks:
            self.url_queue.put(task)
            
        # Spuštění Workerů
        workers = []
        for _ in range(NUM_WORKERS):
            w = Worker(self.url_queue, KEYWORDS, self.results, self.results_lock, self.analyze_text_score)
            w.start()
            workers.append(w)
            
        # Čekání na dokončení
        self.url_queue.join()
        
        self.update_status("HOTOVO! Všechna data analyzována.")
        self.is_running = False

    def update_status(self, text):
        """ Bezpečně aktualizuje text statusu """
        self.lbl_status.config(text=text)

    def update_gui(self):
        """ Periodicky kontroluje nové výsledky a kreslí je do tabulky """
        
        # Zjistíme, kolik řádků už máme v tabulce
        current_rows = len(self.tree.get_children())
        
        # S použitím zámku se podíváme do sdíleného listu results
        with self.results_lock:
            total_results = len(self.results)
            # Pokud přibyly nové výsledky, přidáme je do tabulky
            if total_results > current_rows:
                new_data = self.results[current_rows:]
                for row in new_data:
                    # Vložíme řádek do tabulky
                    self.tree.insert("", tk.END, values=(row['TOTAL_SCORE'], row['STATUS'], row['TITLE'], row['URL']))

        # Pokud proces stále běží, naplánujeme další kontrolu za 100ms
        if self.is_running or current_rows < total_results:
            self.root.after(100, self.update_gui)
        else:
            # Konec
            self.btn_start.config(state=tk.NORMAL)
            messagebox.showinfo("Dokončeno", f"Analýza dokončena.\nZpracováno {total_results} článků.")

if __name__ == "__main__":
    root = tk.Tk()
    app = NewsAnalyzerGUI(root)
    root.mainloop()