# ip_generator.py - CLEANED STREAM IPS
import random
import socket
import time
from queue import Queue
from config import Config

class IPGenerator:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.valid_ips = Queue()
        self.running = True
    
    def check_ip_valid(self, ip):
        try:
            socket.gethostbyaddr(ip)
            return True
        except:
            return False
    
    def check_ip_active(self, ip, timeout=2):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, 80))
            sock.close()
            return result == 0
        except:
            return False
    
    def generate_ips_level1_full(self, base_ip, start_octet=1):
        base_parts = base_ip.split('.')
        if len(base_parts) != 4:
            print("[!] Level 1: Need 4 octets (e.g., 157.7.44.1)")
            return
        
        base_three_octets = '.'.join(base_parts[:3]) + '.'
        valid_count = 0
        
        print(f"[*] LEVEL 1: Scanning IPs from {base_three_octets}[{start_octet}-254]...")
        
        for last_octet in range(start_octet, 255):
            ip = base_three_octets + str(last_octet)
            
            if self.check_ip_valid(ip):
                valid_count += 1
                yield ip, last_octet
                print(f"[+] L1 Valid IP: {ip} ({valid_count} found)")
            else:
                yield None, last_octet
            
            if last_octet % 50 == 0:
                time.sleep(0.5)
        
        print(f"[*] LEVEL 1 completed for base {base_three_octets}")
    
    def generate_ips_level2_explore(self, base_two_octets, max_valid=50):
        valid_count = 0
        attempted = set()
        
        print(f"[*] LEVEL 2 (Explore): Mencari base baru dari {base_two_octets}[1-254].[1-254]...")
        print(f"[*] Hanya IP VALID (ada PTR record) yang akan diproses")
        
        while valid_count < max_valid:
            third_octet = random.randint(1, 254)
            fourth_octet = random.randint(1, 254)
            ip = base_two_octets + str(third_octet) + '.' + str(fourth_octet)
            
            ip_key = f"{third_octet}.{fourth_octet}"
            if ip_key in attempted:
                continue
            
            attempted.add(ip_key)
            
            if self.check_ip_valid(ip):
                valid_count += 1
                yield ip
                print(f"[+] L2 Explore Valid IP: {ip} ({valid_count}/{max_valid})")
            else:
                if valid_count == 0 and len(attempted) % 100 == 0:
                    print(f"[*] L2 Explore: {len(attempted)} IPs checked, {valid_count} valid found...")
            
            if valid_count % 10 == 0 and valid_count > 0:
                time.sleep(0.1)
        
        print(f"[*] LEVEL 2 Explore completed: {valid_count}/{max_valid} valid IPs found")
    
    def generate_ips_level2_exploit_full(self, base_three_octets, start_octet=1):
        valid_count = 0
        
        print(f"[*] LEVEL 2 (Exploit): Scanning IPs from {base_three_octets}[{start_octet}-254]...")
        print(f"[*] Hanya IP VALID (ada PTR record) yang akan diproses")
        
        for last_octet in range(start_octet, 255):
            ip = base_three_octets + str(last_octet)
            
            if self.check_ip_valid(ip):
                valid_count += 1
                yield ip, last_octet
                print(f"[+] L2 Exploit Valid IP: {ip} ({valid_count} found)")
            else:
                yield None, last_octet
            
            if last_octet % 50 == 0:
                time.sleep(0.5)
        
        print(f"[*] LEVEL 2 Exploit completed for base {base_three_octets}")
    
    def get_valid_ips_from_base(self, base_three_octets, max_ips=10, max_attempts=500):
        valid_ips = []
        attempted = set()
        
        print(f"[*] Mencari {max_ips} IP valid dari base {base_three_octets}x...")
        
        for attempt in range(max_attempts):
            if len(valid_ips) >= max_ips:
                break
            
            last_octet = random.randint(1, 254)
            
            if last_octet in attempted:
                continue
            
            attempted.add(last_octet)
            ip = base_three_octets + str(last_octet)
            
            if self.check_ip_valid(ip):
                valid_ips.append(ip)
                print(f"[+] Found valid IP: {ip} ({len(valid_ips)}/{max_ips})")
        
        print(f"[*] Found {len(valid_ips)} valid IPs from {len(attempted)} attempts")
        return valid_ips
    
    def generate_ips(self, base_ip, max_valid=None):
        return self.generate_ips_level1_full(base_ip)
    
    def stream_ips(self, base_ip, callback, max_valid=None):
        for ip, _ in self.generate_ips_level1_full(base_ip):
            if ip:
                callback(ip)
