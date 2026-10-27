# config.py - OPTIMIZED NETWORK & THREADS
import os
import tempfile

class Config:
    MAX_THREADS_REVERSE = 40  
    MAX_THREADS_SCAN = 120     
    
    PREFER_SOCKS5 = True
    SOCKS5_PRIORITY = 0.7
    PROXY_REFRESH_INTERVAL = 1800
    PROXY_URL = "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/all/data.txt"
    
    MAX_VALID_RNG = 50
    MAX_VALID_RNG_LIMIT = 200
    
    MAX_CACHE_SIZE = 10000
    CACHE_CLEANUP_INTERVAL = 3600
    
    TEMP_DIR = os.path.expanduser("~/.mt_scanner_cache/")
    MAX_MEMORY_ITEMS = 5000
    
    OUTPUT_FILES = {
        'movable_type': 'mv.txt',
        'movable_type_v4': 'mv4.txt',
        'processed_ips': 'processed_ips.txt',
        'cache': 'cache.db'
    }
    
    MAX_RETRIES = 2
    RETRY_DELAY = 1
    
    TIMEOUT_REVERSE = 12
    TIMEOUT_SCAN = 5
    
    SAMPLE_SIZE = 10
    MIN_DOMAINS_PER_IP = 20
    MIN_GOOD_SAMPLES = 1
    
    @staticmethod
    def ensure_temp_dir():
        if not os.path.exists(Config.TEMP_DIR):
            os.makedirs(Config.TEMP_DIR)
