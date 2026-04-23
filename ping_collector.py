import subprocess
import pandas as pd
from datetime import datetime
import time
import atexit
import os
from pathlib import Path

CSV_PATH = Path("data/ping_live.csv")

def ping_loop(host, interval=1):
    """Бесконечный цикл пингов"""
    CSV_PATH.parent.mkdir(exist_ok=True)
    
    def cleanup():
        print("🛑 Пинг остановлен")
    
    atexit.register(cleanup)
    
    print(f"📡 Пинг {host} запущен (файл: {CSV_PATH})")
    
    while True:
        try:
            latency = ping_once(host)
            timestamp = datetime.now()
            new_row = pd.DataFrame([{'timestamp': timestamp, 'value': latency}])
            
            # Добавляем в конец файла
            if CSV_PATH.exists():
                new_row.to_csv(CSV_PATH, mode='a', header=False, index=False)
            else:
                new_row.to_csv(CSV_PATH, index=False)
            
            print(f"{timestamp.strftime('%H:%M:%S')} | {latency:.1f if not pd.isna(latency) else 'timeout'} ms")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Ошибка: {e}")
        
        time.sleep(interval)

def ping_once(host):
    """Один пинг"""
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '2', host], 
                               capture_output=True, text=True, timeout=4)
        if result.returncode == 0 and 'time=' in result.stdout:
            return float(result.stdout.split('time=')[1].split(' ms')[0])
    except:
        pass
    return float('nan')

if __name__ == "__main__":
    host = "8.8.8.8"
    ping_loop(host)