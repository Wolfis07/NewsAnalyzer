import requests
from bs4 import BeautifulSoup
from queue import Queue
from threading import Lock
import csv
import sys
import time


from worker import Worker


TARGET_URL = "https://www.theregister.com" 
KEYWORDS = [
    "AI", "Security", "Cloud", "Microsoft", 
    "Linux", "Data", "Cyber", "Chip", "Code"
]
NUM_WORKERS = 4
CSV_HEADERS = ["TITLE", "URL", "TOTAL_SCORE", "STATUS"]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
}

url_queue = Queue()
results = []
results_lock = Lock()



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



def main():
    start_time = time.time()
    
    tasks = [] 
    try:
        print(f"Stahuji novinky z {TARGET_URL}...")
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        
        potential_articles = soup.find_all(['h3', 'h4', 'article'])
        
        print(f"Prohledávám {len(potential_articles)} elementů...")
        
        for item in potential_articles:
            link = item.find('a')
            if link and link.get('href'):
                title = link.text.strip()
                href = link.get('href')
                
                
                if len(title) < 5:
                    continue

                
                if href.startswith('/'):
                    full_url = TARGET_URL + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue 
                
                # Uložíme jen unikátní
                if (title, full_url) not in tasks:
                    tasks.append((title, full_url))

        if not tasks:
            print("VAROVÁNÍ: Nenalezeny žádné články.", file=sys.stderr)
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"CHYBA I/O: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Nalezeno {len(tasks)} unikátních článků. Spouštím analýzu...")
    
    for task in tasks:
        url_queue.put(task)
    
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