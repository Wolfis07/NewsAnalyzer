# news_analyzer.py

import requests
from bs4 import BeautifulSoup
from queue import Queue
from threading import Lock
import csv
import sys
import time

# Import třídy Worker
from worker import Worker

# --- 1. Konfigurace ---
TARGET_URL = "https://www.theverge.com"  # Bez lomítka na konci pro snadnější spojování
KEYWORDS = [
    "AI", "Apple", "Samsung", "Google",
    "Gaming", "SpaceX", "VR", "Cloud", "Review"
]
NUM_WORKERS = 4
CSV_HEADERS = ["TITLE", "URL", "TOTAL_SCORE", "STATUS"]

# Robustní hlavička proti blokování (420 Error)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Sdílené zdroje
url_queue = Queue()
results = []
results_lock = Lock()

# --- 2. Utility Funkce ---

def analyze_text_score(text, keywords):
    text_lower = text.lower()
    return sum(text_lower.count(k.lower()) for k in keywords)

def save_results_to_csv(filename, headers, data):
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        print(f"Ukládání dokončeno do {filename}.")
        return True
    except IOError as e:
        print(f"CHYBA VÝSTUPU: {e}", file=sys.stderr)
        return False

# --- 3. Hlavní Funkce (Producer) ---

def main():
    start_time = time.time()
    
    # PRODUCER: Stahování a extrakce
    tasks = [] 
    try:
        print(f"Stahuji novinky z {TARGET_URL}...")
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # --- OPRAVENÁ STRATEGIE EXTRAKCE ---
        # Hledáme nadpisy H2 a H3, které uvnitř mají odkaz <a>.
        # To je standardní struktura HTML pro články a je mnohem stabilnější.
        headlines = soup.find_all(['h2', 'h3'])
        
        print(f"Prohledávám {len(headlines)} nadpisů...")
        
        for h in headlines:
            link = h.find('a')
            if link and link.get('href') and link.text:
                title = link.text.strip()
                href = link.get('href')
                
                # Oprava relativních URL (pokud odkaz začíná /, přidáme doménu)
                if href.startswith('/'):
                    full_url = TARGET_URL + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue # Ignorujeme divné odkazy
                
                # Filtrace duplicit (set by byl lepší, ale list stačí pro demo)
                if (title, full_url) not in tasks:
                    tasks.append((title, full_url))

        if not tasks:
            print("VAROVÁNÍ: Nenalezeny žádné články. Struktura webu se mohla změnit.", file=sys.stderr)
            # Debug: Vypíšeme část HTML pro kontrolu, pokud se nic nenajde
            # print(soup.prettify()[:1000]) 
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"CHYBA I/O: {e}", file=sys.stderr)
        sys.exit(1)

    # Vložení do fronty
    print(f"Nalezeno {len(tasks)} unikátních článků. Spouštím analýzu...")
    for task in tasks:
        url_queue.put(task)
    
    # Spuštění vláken
    workers = []
    for _ in range(NUM_WORKERS):
        w = Worker(url_queue, KEYWORDS, results, results_lock, analyze_text_score)
        w.start()
        workers.append(w)

    url_queue.join()
    
    if save_results_to_csv("analyzed_news.csv", CSV_HEADERS, results):
        print(f"Hotovo za {time.time() - start_time:.2f} s.")

if __name__ == "__main__":
    main()