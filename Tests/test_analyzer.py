import unittest
from unittest.mock import patch, MagicMock
from queue import Queue 
import news_analyzer
from news_analyzer import analyze_text_score, save_results_to_csv, results, results_lock, url_queue
from worker import Worker

TEST_KEYWORDS = ["Security", "Cloud"]

class TestAnalyzerComponents(unittest.TestCase):
    """ UNIT TESTY: Testuje izolované funkce. """
    
    def test_analyze_text_score_basic(self):
        text = "Cloud Security is important."
        self.assertEqual(analyze_text_score(text, TEST_KEYWORDS), 2)

    def test_analyze_text_score_empty(self):
        self.assertEqual(analyze_text_score("", TEST_KEYWORDS), 0)

    def test_save_csv_permission_error(self):
        """ Testuje, že program nespadne, když nejde zapsat do souboru. """
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            success = save_results_to_csv("test.csv", ["Col1"], [])
            self.assertFalse(success)


class TestAnalyzerIntegration(unittest.TestCase):
    """ INTEGRAČNÍ TESTY: Testuje spolupráci komponent. """
    
    def setUp(self):
        
        results.clear()
        with results_lock:
            
            while not url_queue.empty():
                url_queue.get()
                url_queue.task_done()
        
    @patch('news_analyzer.requests.get')
    @patch('news_analyzer.NUM_WORKERS', 2)
    def test_parallel_analysis_success(self, mock_get):
        """ Testuje úspěšný scénář: Stáhnu -> Rozdělím -> Analyzuji. """
        mock_response = MagicMock()
        mock_response.status_code = 200
        
       
        mock_response.content = b"""
            <html><body>
                <h4><a href="/security/bug">Major Security Bug</a></h4>
                <h3><a href="/cloud/azure">Microsoft Cloud Update</a></h3>
            </body></html>"""
        mock_get.return_value = mock_response

       
        news_analyzer.main()
        
       
        self.assertEqual(len(results), 2)
        scores = {r['TOTAL_SCORE'] for r in results}
        self.assertIn(1, scores)

    @patch('news_analyzer.requests.get')
    def test_no_articles_found(self, mock_get):
        """ Testuje, že se program ukončí, když nenajde žádné články. """
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        mock_response.content = b"<html><body><h1>Maintenance</h1></body></html>"
        mock_get.return_value = mock_response

        with self.assertRaises(SystemExit) as cm:
            news_analyzer.main()
        self.assertEqual(cm.exception.code, 1)

    def test_worker_resilience_on_crash(self):
        """ Testuje, že když analýza spadne, Worker to ustojí a zapíše Error. """
        
        
        def crashing_analysis_func(text, keywords):
            raise ValueError("Simulated Crash!")

       
        local_test_queue = Queue()
        local_test_queue.put(("Bad Title", "http://bad.url"))
        
       
        w = Worker(local_test_queue, [], results, results_lock, crashing_analysis_func)
        w.start()
        
        
        local_test_queue.join()
        
        
        self.assertEqual(len(results), 1)
        self.assertTrue("Error" in results[0]["STATUS"])

if __name__ == '__main__':
    unittest.main()