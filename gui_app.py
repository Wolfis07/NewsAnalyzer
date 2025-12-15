import tkinter as tk
from tkinter import ttk, messagebox
import requests
from bs4 import BeautifulSoup
from queue import Queue
from threading import Thread, Lock
from urllib.parse import urljoin
import time
import sys

# Import tvé existující třídy Worker
from worker import Worker

# --- Konfigurace ---
try:
    from config import TARGET_URL, KEYWORDS, NUM_WORKERS, HEADERS, CSV_FILE
except ImportError:
    TARGET_URL = "https://www.theregister.com"
    KEYWORDS = ["AI", "Security", "Linux"]
    NUM_WORKERS = 4
    HEADERS = {'User-Agent': 'Mozilla/5.0'}
    CSV_FILE = "analyzed_news.csv"

class NewsAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Paralelní News Analyzer")
        self.root.geometry("1000x700")

        self.lock = Lock()
        self.results = []
        self.is_running = False

        # --- 1. ČÁST: KONFIGURACE ---
        config_frame = tk.LabelFrame(root, text="Nastavení Analýzy", padx=10, pady=10)
        config_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(config_frame, text="URL:").grid(row=0, column=0, sticky="w")
        self.url_entry = tk.Entry(config_frame, width=40)
        self.url_entry.insert(0, TARGET_URL)
        self.url_entry.grid(row=0, column=1, padx=5, sticky="w")

        tk.Label(config_frame, text="Klíčová slova:").grid(row=1, column=0, sticky="w")
        self.keywords_entry = tk.Entry(config_frame, width=40)
        self.keywords_entry.insert(0, ", ".join(KEYWORDS))
        self.keywords_entry.grid(row=1, column=1, padx=5, sticky="w")

        tk.Label(config_frame, text="Vlákna:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.workers_entry = tk.Entry(config_frame, width=5)
        self.workers_entry.insert(0, str(NUM_WORKERS))
        self.workers_entry.grid(row=0, column=3, padx=5, sticky="w")

        # --- 2. ČÁST: OVLÁDÁNÍ ---
        control_frame = tk.Frame(root)
        control_frame.pack(pady=5)

        self.start_btn = tk.Button(control_frame, text="Spustit Analýzu", command=self.start_analysis, bg="green", fg="white", font=("Arial", 12, "bold"))
        self.start_btn.pack(side="left", padx=10)

        self.status_label = tk.Label(control_frame, text="Připraveno", fg="gray")
        self.status_label.pack(side="left", padx=10)

        # --- 3. ČÁST: TABULKA ---
        columns = ("score", "status", "title", "url")
        self.tree = ttk.Treeview(root, columns=columns, show="headings")
        
        self.tree.heading("score", text="Skóre")
        self.tree.heading("status", text="Stav")
        self.tree.heading("title", text="Titulek Článku")
        self.tree.heading("url", text="URL")

        self.tree.column("score", width=50, anchor="center")
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("title", width=400)
        self.tree.column("url", width=400)

        scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)

    def log_status(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def analyze_text(self, title, keywords):
        """Funkce pro výpočet skóre."""
        score = 0
        if not title:
            return 0
        title_lower = title.lower()
        for k in keywords:
            if k.lower() in title_lower:
                # --- ZDE JSME VRÁTILI BODOVÁNÍ NA +1 ---
                score += 1 
        return score

    def start_analysis(self):
        if self.is_running:
            return

        current_url = self.url_entry.get()
        keywords_str = self.keywords_entry.get()
        current_keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
        
        try:
            current_workers = int(self.workers_entry.get())
        except ValueError:
            messagebox.showerror("Chyba", "Počet vláken musí být číslo!")
            return

        if current_workers <= 0:
            messagebox.showerror("Chyba", "Počet vláken musí být kladný!")
            return

        for i in self.tree.get_children():
            self.tree.delete(i)
        self.results = [] 
        
        self.is_running = True
        self.start_btn.config(state="disabled")
        self.log_status("Spouštím stahování...")

        self.check_results_loop()

        thread = Thread(target=self.run_process, args=(current_url, current_keywords, current_workers))
        thread.daemon = True
        thread.start()

    def check_results_loop(self):
        if not self.is_running and not self.results:
            return

        current_rows = len(self.tree.get_children())
        
        with self.lock:
            if len(self.results) > current_rows:
                new_items = self.results[current_rows:]
                for item in new_items:
                    self.tree.insert("", "end", values=(
                        item.get('TOTAL_SCORE', 0),
                        item.get('STATUS', ''),
                        item.get('TITLE', ''),
                        item.get('URL', '')
                    ))
        
        if self.is_running or len(self.results) > current_rows:
            self.root.after(100, self.check_results_loop)

    def run_process(self, url, keywords, num_workers):
        try:
            self.log_status(f"Stahuji: {url}")
            headers_local = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers_local)
            
            if response.status_code != 200:
                self.log_status(f"Chyba: {response.status_code}")
                self.finalize()
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            
            queue = Queue()
            count = 0
            found_urls = set()

            # <a href="/bla-bla-bla">Titulek k linku</a>
            for link in soup.find_all('a', href=True):
                href = link['href']
                title_text = link.get_text(strip=True) or "Bez titulku"

                # Inteligentní spojení URL pro případ relativní cesty
                full_link = urljoin(url, href)

                if full_link and full_link.startswith("http") not in found_urls:
                    found_urls.add(full_link)
                    queue.put((title_text, full_link))
                    count += 1
            
            self.log_status(f"Fronta naplněna ({count} pol.). Spouštím workery...")

            threads = []
            for i in range(num_workers):
                worker = Worker(queue, keywords, self.results, self.lock, self.analyze_text)
                worker.start()
                threads.append(worker)

            queue.join()
            self.log_status("Analýza hotova.")
            
        except Exception as e:
            print(f"Chyba: {e}")
            self.log_status(f"Chyba: {e}")
        
        finally:
            self.finalize()

    def finalize(self):
        self.is_running = False
        self.start_btn.config(state="normal")
        self.log_status("Hotovo.")

if __name__ == "__main__":
    root = tk.Tk()
    app = NewsAnalyzerGUI(root)
    root.mainloop()