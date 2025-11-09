import sys, os, gi, json, time
import pyds
from kafka import KafkaProducer

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

# ===============================================================
# KAFKA SETUP (có retry logic)
# ===============================================================
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "infer")

def create_kafka_producer(broker, retries=20, delay=5):
    for i in range(retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=[broker],
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            print(f"✅ Connected to Kafka at {broker}")
            return producer
        except Exception as e:
            print(f"⚠️ Kafka not ready ({e}), retrying in {delay}s... ({i+1}/{retries})")
            time.sleep(delay)
    print("❌ Failed to connect to Kafka after retries. Exiting.")
    sys.exit(1)

producer = create_kafka_producer(KAFKA_BROKER)

# ===============================================================
# INPUT VIDEO
# ===============================================================
VIDEO_PATH = None
if "--video" in sys.argv:
    VIDEO_PATH = sys.argv[sys.argv.index("--video") + 1]
else:
    print("Usage: python3 main.py --video <path_to_video>")
    sys.exit(1)

OUTPUT_PATH = "/output/results.txt"

# metadata for this video
CAM_ID = os.getenv("CAM_ID", "cam_01")
VIDEO_URL = os.getenv("VIDEO_URL", "rtsp://10.0.0.2:8554/cam01")
EXTRA_INFO = {
    "recordingId": f"rec_{time.strftime('%Y%m%d_%H%M%S')}",
    "cameraCode": CAM_ID.upper(),
    "path": VIDEO_PATH,
    "duration": 60.0,
    "startTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "endTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 60))
}

# ===============================================================
# PROBE FUNCTION – xuất JSON format chuẩn
# ===============================================================
def osd_sink_pad_buffer_probe(pad, info, u_data):
    buf = info.get_buffer()
    if not buf:
        return Gst.PadProbeReturn.OK

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buf))
    if not batch_meta:
        return Gst.PadProbeReturn.OK

    l_frame = batch_meta.frame_meta_list

    while l_frame is not None:
        frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        detections = []
        l_obj = frame_meta.obj_meta_list

        while l_obj is not None:
            obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            x1 = float(obj_meta.rect_params.left)
            y1 = float(obj_meta.rect_params.top)
            x2 = x1 + float(obj_meta.rect_params.width)
            y2 = y1 + float(obj_meta.rect_params.height)
            det_time = time.time()

            det = {
                "xyxy": [x1, y1, x2, y2],
                "confidence": float(obj_meta.confidence),
                "class_id": int(obj_meta.class_id),
                "class_name": getattr(obj_meta, "obj_label", f"class_{obj_meta.class_id}"),
                "detect_time": det_time,
                "video_url": VIDEO_URL,
                "cam_id": CAM_ID,
                "frame_id": int(frame_meta.frame_num),
                "push_time": det_time,  # tạm thời = detect_time (update khi gửi)
            }

            # --- optional SGIE placeholders ---
            det["classifier"] = getattr(obj_meta, "classifier_label", None)
            det["classifier_prob"] = getattr(obj_meta, "classifier_confidence", None)
            # Các trường mở rộng (tùy secondary model)
            det["helmet_scores"] = None
            det["vest_scores"] = None
            det["shoes_scores"] = None

            detections.append(det)
            l_obj = l_obj.next

        if detections:
            now = time.time()
            msg = {
                "cam_id": CAM_ID,
                "frame_id": int(frame_meta.frame_num),
                "detections": detections,
                "video_url": VIDEO_URL,
                "push_time": now,
                "extra_information": EXTRA_INFO
            }

            # Gửi Kafka
            try:
                producer.send(KAFKA_TOPIC, msg)
                producer.flush()
                print(f"🟢 Sent frame {frame_meta.frame_num} ({len(detections)} detections) → Kafka '{KAFKA_TOPIC}'")
            except Exception as e:
                print(f"⚠️ Kafka send failed: {e}")

            # Ghi log file
            with open(OUTPUT_PATH, "a") as f:
                f.write(json.dumps(msg) + "\n")

        l_frame = l_frame.next

    return Gst.PadProbeReturn.OK


# ===============================================================
# PIPELINE MAIN
# ===============================================================
def main():
    pipeline = Gst.Pipeline()

    src = Gst.ElementFactory.make("filesrc", "src")
    src.set_property("location", VIDEO_PATH)

    decodebin = Gst.ElementFactory.make("decodebin", "decodebin")
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "nvvidconv")
    capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
    capsfilter.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=NV12"))

    streammux = Gst.ElementFactory.make("nvstreammux", "streammux")
    streammux.set_property("batch-size", 1)
    streammux.set_property("width", 640)
    streammux.set_property("height", 640)
    streammux.set_property("batched-push-timeout", 40000)

    infer = Gst.ElementFactory.make("nvinfer", "primary-infer")
    infer.set_property("config-file-path", "/configs/deepstream_yolov8_config.txt")

    osd = Gst.ElementFactory.make("nvdsosd", "osd")
    sink = Gst.ElementFactory.make("fakesink", "sink")
    sink.set_property("sync", False)

    for elem in [src, decodebin, nvvidconv, capsfilter, streammux, infer, osd, sink]:
        if not elem:
            print("❌ Failed to create GStreamer element")
            sys.exit(1)
        pipeline.add(elem)

    src.link(decodebin)

    def on_pad_added(decodebin, pad):
        print("🔗 New pad from decodebin:", pad.get_name())
        sink_pad = nvvidconv.get_static_pad("sink")
        if not sink_pad.is_linked():
            pad.link(sink_pad)
    decodebin.connect("pad-added", on_pad_added)

    nvvidconv.link(capsfilter)
    capsfilter_src_pad = capsfilter.get_static_pad("src")
    streammux_sink_pad = streammux.get_request_pad("sink_0")
    if capsfilter_src_pad.link(streammux_sink_pad) != Gst.PadLinkReturn.OK:
        print("❌ Failed to link capsfilter → streammux")
        sys.exit(1)

    streammux.link(infer)
    infer.link(osd)
    osd.link(sink)

    infer_src_pad = infer.get_static_pad("src")
    if not infer_src_pad:
        print("❌ Unable to get src pad from nvinfer")
        sys.exit(1)
    infer_src_pad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, None)

    print("🚀 Starting DeepStream inference + Kafka streaming...")
    pipeline.set_state(Gst.State.PLAYING)

    bus = pipeline.get_bus()
    while True:
        msg = bus.timed_pop_filtered(1000, Gst.MessageType.EOS | Gst.MessageType.ERROR)
        if msg:
            if msg.type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                print(f"❌ ERROR: {err}, {debug}")
            break

    pipeline.set_state(Gst.State.NULL)
    print("✅ Done. Results saved at:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
