from threading import Thread
import sys

class Worker(Thread):
    def __init__(self, queue, keywords, results_list, lock, analysis_func):
        Thread.__init__(self)
        self.queue = queue
        self.keywords = keywords
        self.results_list = results_list
        self.lock = lock
        self.analysis_func = analysis_func
        self.daemon = True

    def run(self):
        from queue import Empty
        while True:
            try:
                title, url = self.queue.get(timeout=1) 
                self.process_article(title, url)
                self.queue.task_done()
            except Empty:
                break
            except Exception as e:
                print(f"[{self.name}] Neočekávaná chyba: {e}", file=sys.stderr)
                self.queue.task_done()

    def process_article(self, title, url):
        try:
            score = self.analysis_func(title, self.keywords)
            self._log_result(title, url, score, "OK")
        except Exception as e:
            self._log_result(title, url, 0, f"Error: {type(e).__name__}")

    def _log_result(self, title, url, score, status):
        row = {"TITLE": title, "URL": url, "TOTAL_SCORE": score, "STATUS": status}
        with self.lock: 
            self.results_list.append(row)