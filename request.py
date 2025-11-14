#!/usr/bin/env python3
import json
from kafka import KafkaProducer

KAFKA_BROKER = "172.17.0.1:9092"   # hoặc 172.17.0.1:9092 nếu chạy trong docker
TOPIC = "request_stream"

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def send_video_job(video_path):
    msg = {"video": video_path}
    producer.send(TOPIC, msg)
    producer.flush()
    print(f"📡 Sent job → {TOPIC}: {msg}")

if __name__ == "__main__":
    send_video_job("/ds-app/src/input/sample.mp4")
