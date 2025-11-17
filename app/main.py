#!/usr/bin/env python3
import sys
import os
import json
import time
from kafka import KafkaConsumer
from pipeline import run_pipeline

# ================================================================
# READ KAFKA BROKER FROM ENV (MUST BE SET IN DOCKER-COMPOSE)
# ================================================================
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "172.17.0.1:9092")
REQUEST_TOPIC = "request_stream"

print(f"🔧 Worker starting…")
print(f"📡 Kafka Broker = {KAFKA_BROKER}")
print(f"📨 Subscribed topic = {REQUEST_TOPIC}")

# ================================================================
# CREATE CONSUMER WITH CORRECT BROKER
# ================================================================
# !!! THIS MUST MATCH THE PRODUCER BROKER EXACTLY !!!
# ================================================================

consumer = None
for i in range(20):
    try:
        consumer = KafkaConsumer(
            REQUEST_TOPIC,
            bootstrap_servers=[KAFKA_BROKER],
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        print(f"✅ Worker connected to Kafka at {KAFKA_BROKER}")
        break
    except Exception as e:
        print(f"⚠️ Kafka not ready ({e}), retrying… ({i+1}/20)")
        time.sleep(3)

if consumer is None:
    print("❌ Cannot connect to Kafka → exiting.")
    sys.exit(1)

print("👂 Worker is now listening for video jobs...\n")

# ================================================================
# MAIN LOOP: RECEIVE JOBS → RUN PIPELINE
# ================================================================
for msg in consumer:
    try:
        data = msg.value
        print(f"📩 Received job: {data}")

        video_path = data.get("video")
        if not video_path:
            print("⚠️ Invalid message (missing 'video' field'), skip.")
            continue

        print(f"🎥 Starting pipeline for video: {video_path}")
        run_pipeline(video_path)

        print(f"🏁 Finished job for {video_path}\n")

    except Exception as e:
        print(f"❌ Worker error: {e}")
