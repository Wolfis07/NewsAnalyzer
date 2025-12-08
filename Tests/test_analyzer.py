import unittest
import sys
import os

# Zajištění, že Python vidí 'config.py' v nadřazené složce
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from config import TARGET_URL, KEYWORDS, NUM_WORKERS
except ImportError:
    TARGET_URL = None
    KEYWORDS = []

class TestConfiguration(unittest.TestCase):
    
    def test_config_variables_exist(self):
        """Testuje, zda byly proměnné z configu úspěšně načteny."""
        self.assertIsNotNone(TARGET_URL, "TARGET_URL nebyla načtena")
        self.assertTrue(len(KEYWORDS) > 0, "Seznam KEYWORDS je prázdný")
        self.assertGreater(NUM_WORKERS, 0, "Počet workerů musí být větší než 0")

    def test_target_url_validity(self):
        """Jednoduchá kontrola, že URL vypadá validně (začíná http)."""
        self.assertTrue(TARGET_URL.startswith("http"), "URL musí začínat na http/https")

if __name__ == '__main__':
    unittest.main()