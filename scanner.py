# scanner.py - DIRECT PROCESSING WITHOUT IP CACHE CHECK
import requests
import re
import time
import socket
import threading
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from fake_useragent import UserAgent
from urllib3.exceptions import InsecureRequestWarning
from urllib.parse import urlparse
from config import Config

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class MovableTypeScanner:
    def __init__(self, proxy_manager, cache_manager, main_reference=None):
        self.ua = UserAgent()
        self.proxy_manager = proxy_manager
        self.cache_manager = cache_manager
        self.main = main_reference
        self.lock = threading.Lock()
        
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
            "Connection": "close"
        }
        
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=100, 
            pool_maxsize=250, 
            max_retries=1
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.output_files = Config.OUTPUT_FILES
    
    def _report_error(self, err):
        if not self.main:
            return
        if isinstance(err, requests.exceptions.Timeout):
            self.main.increment_timeout()
        else:
            self.main.increment_fail()

    def get_base_url_with_www(self, domain):
        cache_key = f"base_{domain}"
        cached = self.cache_manager.get_reverse_cache(cache_key)
        if cached:
            return cached
        
        try:
            url = f"http://www.{domain}"
            response = self.session.get(
                url, timeout=4, verify=False, allow_redirects=True,
                headers={"User-Agent": self.ua.random}
            )
            if response.status_code < 400:
                final_url = response.url
                self.cache_manager.save_reverse_cache(cache_key, final_url, 'base')
                return final_url
        except Exception as e:
            self._report_error(e)
        return None
    
    def check_rsd_xml(self, domain):
        paths = ['/rsd.xml', '/blog/rsd.xml', '/news/rsd.xml', '/blog1/rsd.xml', 
                 '/diary/rsd.xml', '/mt/rsd.xml', '/kanri/rsd.xml']
        
        base_url = self.get_base_url_with_www(domain)
        if not base_url:
            return None, None
        
        parsed = urlparse(base_url)
        base_domain = parsed.netloc
        protocol = parsed.scheme
        
        for path in paths:
            try:
                url = f"{protocol}://{base_domain}{path}"
                headers = self.headers.copy()
                headers["User-Agent"] = self.ua.random
                
                response = self.session.get(
                    url, headers=headers, 
                    timeout=Config.TIMEOUT_SCAN, 
                    verify=False, allow_redirects=False
                )
                
                if response.status_code == 200 and 'rsd' in response.text.lower():
                    return response.text, url
            except Exception as e:
                self._report_error(e)
                continue
        return None, None
    
    def reverse_ip_tntcode(self, ip):
        last_proxy = None
        for attempt in range(Config.MAX_RETRIES):
            proxy_dict = None
            try:
                url = f"https://domains.tntcode.com/ip/{ip}"
                proxy_dict = self.proxy_manager.get_proxy_for_retry(attempt, last_proxy)
                last_proxy = list(proxy_dict.values())[0] if proxy_dict else None
                
                start_time = time.time()
                headers = self.headers.copy()
                headers["User-Agent"] = self.ua.random
                
                response = self.session.get(
                    url, headers=headers, proxies=proxy_dict,
                    timeout=Config.TIMEOUT_REVERSE, verify=False
                )
                
                if proxy_dict:
                    self.proxy_manager.update_stats(list(proxy_dict.values())[0], True, time.time() - start_time)
                
                if response.status_code != 200:
                    return [], f"HTTP_{response.status_code}"
                
                domains = re.findall(r'<a href="/domain/(.+?)"', response.text)
                return domains, "SUCCESS"
                
            except requests.exceptions.Timeout:
                self._report_error(requests.exceptions.Timeout())
                if proxy_dict:
                    self.proxy_manager.update_stats(list(proxy_dict.values())[0], False)
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                    continue
                return [], "TIMEOUT"
            except Exception as e:
                self._report_error(e)
                if proxy_dict:
                    self.proxy_manager.update_stats(list(proxy_dict.values())[0], False)
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                    continue
                return [], f"ERROR_{str(e)[:20]}"
        return [], "FAILED_MAX_RETRIES"

    def reverse_ip_hackertarget(self, ip):
        last_proxy = None
        for attempt in range(Config.MAX_RETRIES):
            proxy_dict = None
            try:
                url = f"https://api.hackertarget.com/reverseiplookup/?q={ip}"
                proxy_dict = self.proxy_manager.get_proxy_for_retry(attempt, last_proxy)
                last_proxy = list(proxy_dict.values())[0] if proxy_dict else None
                
                start_time = time.time()
                headers = self.headers.copy()
                headers["User-Agent"] = self.ua.random
                
                response = self.session.get(
                    url, headers=headers, proxies=proxy_dict,
                    timeout=Config.TIMEOUT_REVERSE, verify=False
                )
                
                if proxy_dict:
                    self.proxy_manager.update_stats(list(proxy_dict.values())[0], True, time.time() - start_time)
                
                if response.status_code != 200:
                    return [], f"HTTP_{response.status_code}"
                
                if response.text and "error" not in response.text.lower():
                    domains = [d.strip() for d in response.text.strip().split('\n') if d.strip()]
                    return domains, "SUCCESS"
                else:
                    return [], f"API_ERROR_MSG: {response.text.strip()[:30]}"
                    
            except requests.exceptions.Timeout:
                self._report_error(requests.exceptions.Timeout())
                if proxy_dict:
                    self.proxy_manager.update_stats(list(proxy_dict.values())[0], False)
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                    continue
                return [], "TIMEOUT"
            except Exception as e:
                self._report_error(e)
                if proxy_dict:
                    self.proxy_manager.update_stats(list(proxy_dict.values())[0], False)
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                    continue
                return [], f"ERROR_{str(e)[:20]}"
        return [], "FAILED_MAX_RETRIES"
    
    def extract_mt_info(self, rsd_content):
        info = {'engine': None, 'api_link': None, 'version': None}
        engine_match = re.search(r'<engineName>(.+?)</engineName>', rsd_content, re.IGNORECASE)
        if engine_match:
            info['engine'] = engine_match.group(1)
            if 'movable type' in info['engine'].lower():
                version_match = re.search(r'(\d+\.\d+)', info['engine'])
                if version_match:
                    info['version'] = version_match.group(1)
        
        api_match = re.search(r'<api[^>]*apiLink="([^"]+)"[^>]*>', rsd_content, re.IGNORECASE)
        if api_match:
            info['api_link'] = api_match.group(1).strip()
        return info
    
    def check_mt_endpoints(self, domain, mt_info):
        results = []
        if mt_info['api_link']:
            xmlrpc_urls = []
            if mt_info['api_link'].startswith('http'):
                xmlrpc_urls.append(mt_info['api_link'])
            else:
                base_url = self.get_base_url_with_www(domain)
                if base_url:
                    parsed = urlparse(base_url)
                    xmlrpc_urls.append(f"{parsed.scheme}://{parsed.netloc}{mt_info['api_link']}")
            
            for xmlrpc_url in xmlrpc_urls:
                try:
                    headers = self.headers.copy()
                    headers["User-Agent"] = self.ua.random
                    
                    response = self.session.get(
                        xmlrpc_url, headers=headers, timeout=Config.TIMEOUT_SCAN,
                        allow_redirects=False, verify=False
                    )
                    
                    is_v4 = mt_info.get('version') and mt_info['version'].startswith('4')
                    
                    if response.status_code in [403, 411, 405]:
                        url_key = f"{xmlrpc_url}|{response.status_code}"
                        if not self.cache_manager.is_url_scanned(url_key):
                            self.cache_manager.save_scan_result(url_key)
                            
                            with open(self.output_files['movable_type'], 'a') as f:
                                f.write(f"{xmlrpc_url}\n")
                            
                            if self.main:
                                self.main.increment_mt()
                            
                            display_url = xmlrpc_url.replace('http://', '').replace('https://', '')
                            print(f"\n[+] MT ditemukan: {display_url} ({response.status_code})")
                            
                            results.append({
                                'domain': domain,
                                'xmlrpc_url': xmlrpc_url,
                                'xmlrpc_status': response.status_code,
                                'version': mt_info.get('version'),
                                'is_v4': is_v4
                            })
                    
                    if is_v4 and 'mt-xmlrpc.cgi' in xmlrpc_url:
                        upgrade_url = xmlrpc_url.replace('mt-xmlrpc.cgi', 'mt-upgrade.cgi')
                        if upgrade_url != xmlrpc_url:
                            try:
                                upgrade_response = self.session.get(
                                    upgrade_url, headers=headers, timeout=Config.TIMEOUT_SCAN,
                                    allow_redirects=False, verify=False
                                )
                                
                                if upgrade_response.status_code == 200:
                                    upgrade_key = f"{upgrade_url}|200"
                                    if not self.cache_manager.is_url_scanned(upgrade_key):
                                        self.cache_manager.save_scan_result(upgrade_key)
                                        
                                        with open(self.output_files['movable_type_v4'], 'a') as f:
                                            f.write(f"{upgrade_url}\n")
                                        
                                        if self.main:
                                            self.main.increment_mtv4()
                                        
                                        display_upgrade = upgrade_url.replace('http://', '').replace('https://', '')
                                        print(f"\n[!] MT v4 upgrade.cgi: {display_upgrade}")
                            except Exception as e:
                                self._report_error(e)
                except Exception as e:
                    self._report_error(e)
                    continue
        return results
    
    def scan_domain(self, domain):
        try:
            rsd_content, rsd_url = self.check_rsd_xml(domain)
            if rsd_content:
                mt_info = self.extract_mt_info(rsd_content)
                if mt_info['engine'] and 'movable type' in mt_info['engine'].lower():
                    return self.check_mt_endpoints(domain, mt_info)
        except Exception as e:
            self._report_error(e)
        return []
    
    def process_ip(self, ip):
        # Pengecekan is_ip_processed dan mark_ip_processed dihapus total
        if self.main:
            self.main.total_ips_processed += 1
            self.main.update_status_bar()
        
        print(f"\n[*] Processing IP: {ip}")
        
        domains_tnt, status_tnt = self.reverse_ip_tntcode(ip)
        time.sleep(0.3)
        domains_ht, status_ht = self.reverse_ip_hackertarget(ip)
        
        is_tnt_fail = status_tnt != "SUCCESS" and len(domains_tnt) == 0
        is_ht_fail = status_ht != "SUCCESS" and len(domains_ht) == 0
        
        if is_tnt_fail and is_ht_fail:
            print(f"[-] Reverse IP GAGAL total untuk {ip} | TNT Status: {status_tnt} | HT Status: {status_ht}")
            return
        
        domain_set = set()
        all_domains = []
        for d in domains_tnt + domains_ht:
            if d not in domain_set:
                domain_set.add(d)
                all_domains.append(d)
        
        if all_domains:
            print(f"[+] Total domains: {len(all_domains)} (TNT: {len(domains_tnt)} [{status_tnt}], HT: {len(domains_ht)} [{status_ht}])")
            found_count = 0
            with ThreadPoolExecutor(max_workers=Config.MAX_THREADS_SCAN) as executor:
                futures = [executor.submit(self.scan_domain, domain) for domain in all_domains]
                for future in as_completed(futures):
                    results = future.result()
                    if results:
                        found_count += len(results)
            
            print(f"[+] IP {ip}: {found_count} MT found")
        else:
            print(f"[!] No Domains For IP: {ip} (TNT: {status_tnt}, HT: {status_ht})")
