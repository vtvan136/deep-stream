from kafka import KafkaConsumer
import json
import time

KAFKA_BROKER = "localhost:9092"   # hoặc 172.17.0.1:9092 nếu bạn chạy trong bridge khác
KAFKA_TOPIC = "infer"

def main():
    print(f"🔗 Connecting to Kafka broker at {KAFKA_BROKER}...")
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',     # 'earliest' nếu muốn đọc từ đầu
        enable_auto_commit=True,
        group_id="debug-consumer"
    )
    print(f"✅ Connected. Listening to topic '{KAFKA_TOPIC}'...\n")

    for msg in consumer:
        data = msg.value
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"\n🕒 [{ts}] Received message:")
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
