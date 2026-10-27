# proxy_manager.py - NO DOWNLOAD CAPPING, WITH 5000 STATS CAPPING
import threading
import time
import random
import requests
from queue import Queue
from collections import defaultdict
from config import Config

class ProxyManager:
    def __init__(self):
        self.proxy_list = []
        self.socks5_proxies = []
        self.http_proxies = []
        self.proxy_stats = defaultdict(lambda: {
            'success': 0, 'fail': 0, 'total_time': 0,
            'avg_time': 1.0, 'weight': 1.0, 'last_used': 0,
            'proxy_type': 'http'
        })
        self.lock = threading.Lock()
        self.running = True
        self.last_refresh = 0
        
        self.min_weight = 0.1
        self.max_weight = 3.0
        self.socks5_priority = 0.7
        self.max_stats_limit = 5000
        
        self.start_auto_refresh()
    
    def parse_proxy_string(self, proxy_str):
        proxy_str = proxy_str.strip()
        if 'socks5://' in proxy_str.lower():
            return {'url': proxy_str, 'type': 'socks5'}
        elif 'socks4://' in proxy_str.lower():
            return {'url': proxy_str, 'type': 'socks5'}
        elif 'http://' in proxy_str.lower() or 'https://' in proxy_str.lower():
            return {'url': proxy_str, 'type': 'http'}
        else:
            return {'url': f'http://{proxy_str}', 'type': 'http'}
    
    def download_proxies(self):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(
                Config.PROXY_URL, 
                headers=headers, 
                timeout=20, 
                verify=False
            )
            
            if response.status_code == 200:
                raw_lines = [line.strip() for line in response.text.split('\n') if line.strip()]
                
                socks5_temp = []
                http_temp = []
                
                for proxy in raw_lines:
                    parsed = self.parse_proxy_string(proxy)
                    if parsed['type'] == 'socks5':
                        socks5_temp.append(parsed['url'])
                    else:
                        http_temp.append(parsed['url'])
                
                proxies = socks5_temp + http_temp
                
                with self.lock:
                    new_proxies = set(proxies)
                    
                    self.socks5_proxies = socks5_temp
                    self.http_proxies = http_temp
                    self.proxy_list = proxies
                    
                    for proxy in new_proxies:
                        if proxy not in self.proxy_stats:
                            parsed = self.parse_proxy_string(proxy)
                            self.proxy_stats[proxy] = {
                                'success': 0, 'fail': 0, 'total_time': 0,
                                'avg_time': 1.0, 'weight': 1.0, 'last_used': 0,
                                'proxy_type': parsed['type']
                            }
                    
                    if len(self.proxy_stats) > self.max_stats_limit:
                        sorted_proxies = sorted(
                            self.proxy_stats.items(),
                            key=lambda x: x[1]['weight']
                        )
                        excess = len(self.proxy_stats) - self.max_stats_limit
                        for p, _ in sorted_proxies[:excess + 200]:
                            if p in self.proxy_stats:
                                del self.proxy_stats[p]
                
                print(f"[+] Proxy Manager: Loaded {len(socks5_temp)} SOCKS5, {len(http_temp)} HTTP proxies. Active Stats Tracked: {len(self.proxy_stats)}")
                return proxies
        except Exception as e:
            print(f"[-] Proxy download error: {str(e)[:50]}")
            return self.proxy_list
    
    def refresh_proxies(self):
        while self.running:
            time.sleep(Config.PROXY_REFRESH_INTERVAL)
            print("\n[*] Refreshing proxy list...")
            self.download_proxies()
    
    def start_auto_refresh(self):
        self.download_proxies()
        refresh_thread = threading.Thread(target=self.refresh_proxies, daemon=True)
        refresh_thread.start()
    
    def update_stats(self, proxy, success, response_time=None):
        if proxy not in self.proxy_stats:
            return
            
        with self.lock:
            stats = self.proxy_stats[proxy]
            stats['last_used'] = time.time()
            
            if success:
                stats['success'] += 1
                if response_time:
                    total = stats['total_time'] + response_time
                    count = stats['success'] + stats['fail']
                    stats['avg_time'] = total / count if count > 0 else response_time
                    stats['total_time'] = total
                    
                if stats['proxy_type'] == 'socks5':
                    stats['weight'] *= 1.15
            else:
                stats['fail'] += 1
                if stats['proxy_type'] == 'socks5':
                    stats['weight'] *= 0.5
                else:
                    stats['weight'] *= 0.2
            
            total_reqs = stats['success'] + stats['fail']
            if total_reqs > 0:
                success_rate = stats['success'] / total_reqs
                speed_score = 1.0 / stats['avg_time'] if stats['avg_time'] > 0 else 1.0
                speed_score = min(speed_score, 2.0)
                
                weight = (success_rate * 0.7 + speed_score * 0.3) * 2
                stats['weight'] = max(self.min_weight, min(self.max_weight, weight))
                
                if stats['proxy_type'] == 'socks5':
                    stats['weight'] = min(self.max_weight, stats['weight'] * 1.3)
    
    def get_proxy(self, prefer_socks5=True):
        with self.lock:
            if not self.proxy_list:
                return None
            
            if prefer_socks5 and self.socks5_proxies:
                if random.random() < self.socks5_priority:
                    socks5_with_stats = [p for p in self.socks5_proxies if p in self.proxy_stats]
                    if socks5_with_stats:
                        total_weight = sum(self.proxy_stats[p]['weight'] for p in socks5_with_stats)
                        if total_weight > 0:
                            r = random.uniform(0, total_weight)
                            cumulative = 0
                            for proxy in socks5_with_stats:
                                cumulative += self.proxy_stats[proxy]['weight']
                                if r <= cumulative:
                                    return {"http": proxy, "https": proxy}
                    return {"http": random.choice(self.socks5_proxies), "https": random.choice(self.socks5_proxies)}
            
            http_with_stats = [p for p in self.http_proxies if p in self.proxy_stats]
            if http_with_stats:
                total_weight = sum(self.proxy_stats[p]['weight'] for p in http_with_stats)
                if total_weight > 0:
                    r = random.uniform(0, total_weight)
                    cumulative = 0
                    for proxy in http_with_stats:
                        cumulative += self.proxy_stats[proxy]['weight']
                        if r <= cumulative:
                            return {"http": proxy, "https": proxy}
            
            if self.proxy_list:
                proxy = random.choice(self.proxy_list)
                return {"http": proxy, "https": proxy}
            return None
    
    def get_different_proxy(self, last_proxy=None):
        with self.lock:
            if not self.proxy_list:
                return None
            available = [p for p in self.proxy_list if p != last_proxy]
            if not available:
                available = self.proxy_list
            
            socks5_available = [p for p in available if p in self.socks5_proxies]
            if socks5_available and random.random() < self.socks5_priority:
                return {"http": random.choice(socks5_available), "https": random.choice(socks5_available)}
            
            proxy = random.choice(available)
            return {"http": proxy, "https": proxy}
    
    def get_proxy_for_retry(self, retry_count, last_proxy=None):
        with self.lock:
            if not self.proxy_list:
                return None
            available = self.proxy_list
            if last_proxy:
                available = [p for p in self.proxy_list if p != last_proxy]
            if not available:
                available = self.proxy_list
            
            if retry_count < 2:
                socks5_available = [p for p in available if p in self.socks5_proxies]
                if socks5_available:
                    return {"http": random.choice(socks5_available), "https": random.choice(socks5_available)}
            
            proxy = random.choice(available)
            return {"http": proxy, "https": proxy}
    
    def print_stats(self):
        print("\n" + "═"*60)
        print(" PROXY STATISTICS (Top 10)")
        print("═"*60)
        print(f"📡 SOCKS5 Available: {len(self.socks5_proxies)} | HTTP: {len(self.http_proxies)} | Tracked Stats: {len(self.proxy_stats)}")
        print("─"*60)
        with self.lock:
            sorted_proxies = sorted(
                [(p, s) for p, s in self.proxy_stats.items() if p in self.proxy_list],
                key=lambda x: x[1]['weight'],
                reverse=True
            )[:10]
            for proxy, stats in sorted_proxies:
                total = stats['success'] + stats['fail']
                if total > 0:
                    success_rate = (stats['success'] / total) * 100
                    icon = "🔒" if stats['proxy_type'] == 'socks5' else "🌐"
                    print(f"{icon} {proxy[:55]}")
                    print(f"   Success: {stats['success']} | Fail: {stats['fail']} | Rate: {success_rate:.1f}%")
                    print(f"   Avg Time: {stats['avg_time']:.2f}s | Weight: {stats['weight']:.2f}\n")
    
    def cleanup(self):
        self.running = False
