import os
from datetime import datetime, timedelta
import random
import socket
import time

if __name__ == "__main__":
    postgres_host = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
    started_at = datetime.utcnow()
    while datetime.utcnow() < started_at + timedelta(minutes=5):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((postgres_host, postgres_port))
                print(f"Postgres had started at {postgres_host}:{postgres_port}")
                break
        except socket.error:
            print(f"Waiting for postgres at {postgres_host}:{postgres_port}")
            time.sleep(0.5 + (random.randint(0, 100) / 1000))
