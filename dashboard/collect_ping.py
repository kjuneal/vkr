import subprocess
import pandas as pd
from datetime import datetime
import time
import os
import signal
import sys

def ping_once(host='8.8.8.8'):
    """Выполняет один ping и возвращает задержку или NaN"""
    try:
        # Windows команда ping
        result = subprocess.run(
            ['ping', '-n', '1', '-w', '3000', host],  # -n 1 = 1 ping, -w 3000 = 3 сек timeout
            capture_output=True, 
            text=True, 
            timeout=5
        )
        
        output = result.stdout.lower()
        if result.returncode == 0 and 'время=' in output:  # Windows: "время=XXмс"
            # Парсим "время=24мс" или "время=<1мс"
            time_part = output.split('время=')[1].split('мс')[0].strip()
            if time_part == '<1':
                return 0.5  # Принимаем как 0.5мс
            return float(time_part.replace(',', '.'))
        else:
            return float('nan')
    except:
        return float('nan')

def ping_loop(host, csv_path, interval=1):
    """Пинг в отдельный CSV для каждого источника"""
    global ping_running
    csv_path.parent.mkdir(exist_ok=True)
    
    while ping_running:
        try:
            latency = ping_once(host)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            
            new_row = pd.DataFrame([{
                'timestamp': timestamp,
                'value': latency if not pd.isna(latency) else 0
            }])
            
            # Дописываем без заголовка
            if csv_path.exists():
                new_row.to_csv(csv_path, mode='a', header=False, index=False)
            else:
                new_row.to_csv(csv_path, index=False)
                
        except:
            pass
        
        time_module.sleep(interval)

def main(duration_minutes=60, interval_sec=1, host='8.8.8.8'):
    print(f"🚀 Сбор пингов {host} на {duration_minutes} минут")
    print(f"Интервал: {interval_sec} сек, всего точек: {duration_minutes*60//interval_sec}")
    
    data = []
    start_time = datetime.now()
    
    try:
        for i in range(duration_minutes * 60 // interval_sec):
            latency = ping_once(host)
            timestamp = datetime.now()
            
            data.append({
                'timestamp': timestamp,
                'value': latency
            })
            
            # ИСПРАВЛЕННАЯ СТРОКА
            latency_display = f"{latency:.1f}" if not pd.isna(latency) else "timeout"
            print(f"{timestamp.strftime('%H:%M:%S')} | ping #{i+1:4d} | {latency_display} ms")
            
            if i % 60 == 0:  # Сохраняем каждую минуту
                temp_df = pd.DataFrame(data)
                temp_df.to_csv(f'ping_{host.replace(".", "_")}_progress.csv', index=False)
            
            time.sleep(interval_sec)
            
    except KeyboardInterrupt:
        print("\n⏹️ Остановлено пользователем")
    
    # Финальное сохранение
    df = pd.DataFrame(data)
    filename = f'ping_{host.replace(".", "_")}_{duration_minutes}min.csv'
    df.to_csv(filename, index=False)
    
    print(f"\n✅ Сохранено {len(df)} записей в {filename}")
    print(df.describe())
    print(f"Старт: {start_time}")
    print(f"Финиш: {datetime.now()}")
    print(f"Средняя задержка: {df['value'].mean():.2f} ms")
    print(f"Выбросов (>3σ): {(df['value'] > df['value'].mean() + 3*df['value'].std()).sum()}")

if __name__ == "__main__":
    # Запуск: python collect_ping.py [минуты] [интервал_сек] [хост]
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    host = sys.argv[3] if len(sys.argv) > 3 else '8.8.8.8'
    
    main(minutes, interval, host)