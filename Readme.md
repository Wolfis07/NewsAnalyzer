# Dokumentace projektu: Paralelní News Analyzer

| Položka | Hodnota |
| :--- | :--- |
| **Název projektu:** | Paralelní News Analyzer |
| **Autor:** | Matěj Hodek |
| **Kontaktní údaje:** | matejhodek005@gmail.com |
| **Škola:** | SPŠE Ječná |
| **Předmět:** | Programové vybavení |
| **Datum vypracování:** | 8. 12. 2025 |
| **Typ projektu:** | **Školní projekt** |

---

## 1. Specifikace požadavků (Functional Requirements)
Cílem projektu je vytvoření desktopové aplikace pro **paralelní stahování a analýzu novinek** z webových stránek. Aplikace umožňuje uživateli sledovat průběh analýzy v reálném čase.

### Funkční požadavky:
* **Univerzální parsing:** Aplikace musí přijmout URL (např. *The Register*, *iDNES*), stáhnout hlavní stránku a extrahovat odkazy na články.
* **Paralelní zpracování:** Analýza textu jednotlivých článků musí probíhat ve více vláknech (multithreading) pro zrychlení procesu.
* **Scoring systém:** Každý článek získá skóre (+1 bod) za každý výskyt definovaného klíčového slova v titulku.
* **GUI Konfigurace:** Uživatel musí mít možnost měnit URL, klíčová slova a počet vláken (Workers) přímo v grafickém rozhraní.
* **Zobrazení výsledků:** Výsledky (Skóre, Stav, Titulek, URL) se vypisují do interaktivní tabulky.

### Use Case Diagram
Uživatel spustí aplikaci, upraví konfiguraci a spustí analýzu. Systém automaticky provede stahování a vyhodnocení.

![Use Case Diagram](image.png)

---

## 2. Architektura aplikace
Aplikace je navržena jako **Desktopová GUI aplikace** v jazyce Python s využitím modelu **Producer-Consumer** pro paralelizaci.

### Hlavní komponenty:
1.  **GUI Controller (`gui_app.py`):**
    * Zajišťuje vykreslování okna (Tkinter).
    * Řídí hlavní vlákno (Main Thread).
    * Funguje jako *Producer* – stahuje hlavní stránku, parsuje odkazy a plní je do fronty (`Queue`).
    * Periodicky kontroluje výsledky a aktualizuje tabulku.
2.  **Worker Thread (`worker.py`):**
    * Třída dědící z `threading.Thread`.
    * Funguje jako *Consumer* – vybírá URL z fronty a analyzuje je.
    * Využívá zámek (`Lock`) pro bezpečný zápis výsledků do sdílené paměti.
3.  **Konfigurace (`config.py`):**
    * Uchovává výchozí konstanty a nastavení, které se načtou při startu, pokud nejsou přepsány uživatelem v GUI.

### Schéma komunikace:
`GUI (Start)` -> `Requests (Get HTML)` -> `Queue (Fill URLs)` -> `Workers (Process)` -> `Shared List (Results)` -> `GUI (Update Treeview)`

---

## 3. Použité technologie a závislosti
Projekt využívá následující knihovny a protokoly:

### Jazyk a Standardní knihovna:
* **Python 3.x**
* `tkinter`: Grafické uživatelské rozhraní.
* `threading`, `queue`: Správa vláken a synchronizace.
* `urllib.parse`: Manipulace a spojování URL adres.

### Externí závislosti (3rd party):
* **requests**: Pro provádění HTTP/HTTPS požadavků.
* **beautifulsoup4 (bs4)**: Pro parsování HTML a extrakci dat z DOM.

*Seznam závislostí je uveden v souboru `requirements.txt`.*

---

## 4. Konfigurace
Aplikace podporuje dva způsoby konfigurace:

1.  **Souborová konfigurace (`config.py`):**
    Obsahuje výchozí hodnoty pro start aplikace.
    * `TARGET_URL`: Výchozí adresa.
    * `KEYWORDS`: Seznam hledaných slov.
    * `NUM_WORKERS`: Počet vláken.
2.  **Runtime Konfigurace (GUI):**
    Uživatel může před spuštěním analýzy přepsat všechny výše uvedené hodnoty přímo v okně aplikace. Tyto změny mají přednost před souborem `config.py`.

---

## 5. Instalace a spuštění

### 5.1 Prerekvizity
* Nainstalovaný Python 3.8 nebo novější.
* Přístup k internetu.

### 5.2 Instalace
Otevřete terminál v kořenové složce projektu a nainstalujte závislosti:
```bash
pip install -r requirements.txt