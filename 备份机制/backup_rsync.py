import time
import subprocess
import datetime
import os
import sys

# 配置部分
TARGET_HOUR = 0  # 目标执行小时 (0-23)
TARGET_MINUTE = 0 # 目标执行分钟 (0-59)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_SCRIPT = os.path.join(SCRIPT_DIR, "../备份机制/remote_sync_backup.sh")

def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()

def get_seconds_until_next_run():
    """计算距离下一次目标时间还有多少秒"""
    now = datetime.datetime.now()
    target_time = now.replace(hour=TARGET_HOUR, minute=TARGET_MINUTE, second=0, microsecond=0)
    
    # 如果目标时间已经过了（比如现在是 10:00，目标是 00:00），则设为明天的这个时间
    if target_time <= now:
        target_time += datetime.timedelta(days=1)
        
    seconds_remaining = (target_time - now).total_seconds()
    return seconds_remaining

def run_backup():
    log("Starting backup process...")
    try:
        # 使用 bash 执行备份脚本
        result = subprocess.run(["/bin/bash", BACKUP_SCRIPT], check=True, text=True, capture_output=True)
        log("Backup completed successfully.")
        log(f"Output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        log(f"Backup failed with exit code {e.returncode}")
        log(f"Error output:\n{e.stderr}")
    except Exception as e:
        log(f"An unexpected error occurred: {e}")

def main():
    log("Backup Daemon Started (Smart Sleep Mode).")
    log(f"Scheduled daily backup at: {TARGET_HOUR:02d}:{TARGET_MINUTE:02d}")
    
    while True:
        # 1. 计算要睡多久
        sleep_seconds = get_seconds_until_next_run()
        
        # 为了容错，多睡 10 分钟，确保醒来时肯定过了时间点
        sleep_seconds += 600
        
        log(f"Sleeping for {sleep_seconds/3600:.2f} hours until next backup...")
        
        #2. 长眠
        time.sleep(sleep_seconds)
        
        # 3. 醒来干活
        run_backup()

    

if __name__ == "__main__":
    if os.path.exists(BACKUP_SCRIPT):
        os.chmod(BACKUP_SCRIPT, 0o755)
    else:
        log(f"Error: Script not found at {BACKUP_SCRIPT}")
        sys.exit(1)
        
    try:
        main()
    except KeyboardInterrupt:
        log("Daemon stopped by user.")