# cleanup.py - CLEANED TEMP & DB OPTIMIZATION
import os
import shutil
import sqlite3
import time
from config import Config

def cleanup_temp_files():
    """Bersihkan file temporary"""
    print("[*] Cleaning up temporary files...")
    
    if os.path.exists(Config.TEMP_DIR):
        size = sum(os.path.getsize(f) for f in os.listdir(Config.TEMP_DIR) 
                   if os.path.isfile(os.path.join(Config.TEMP_DIR, f)))
        size_mb = size / (1024 * 1024)
        
        shutil.rmtree(Config.TEMP_DIR)
        print(f"[✓] Removed {Config.TEMP_DIR} ({size_mb:.2f} MB)")
    
    db_path = os.path.join(Config.TEMP_DIR, Config.OUTPUT_FILES['cache'])
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute('VACUUM')
        conn.close()
        print("[✓] Database optimized")

def cleanup_old_entries(days=7):
    """Hapus entries lama dari database"""
    db_path = os.path.join(Config.TEMP_DIR, Config.OUTPUT_FILES['cache'])
    if not os.path.exists(db_path):
        print("[!] Database not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(
        'DELETE FROM scan_results WHERE timestamp < ?',
        (time.time() - (days * 86400),)
    )
    scan_count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"[✓] Removed {scan_count} scan result entries")

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════╗
    ║     Movable Type Scanner Cleanup     ║
    ╚══════════════════════════════════════╝
    """)
    
    print("1. Clean all temporary files")
    print("2. Clean entries older than 7 days")
    print("3. Both")
    
    choice = input("\nChoice: ").strip()
    
    if choice in ['1', '3']:
        cleanup_temp_files()
    
    if choice in ['2', '3']:
        cleanup_old_entries()
    
    print("\n[✓] Cleanup completed")
