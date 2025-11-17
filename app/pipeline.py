#!/usr/bin/env python3
import sys
import os
import gi
import json
import time
import pyds
from kafka import KafkaProducer
from datetime import datetime, timezone, timedelta

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# ===============================================================
# INIT GST
# ===============================================================
Gst.init(None)

VN_TZ = timezone(timedelta(hours=7))
def now_vn():
    return datetime.now(VN_TZ).isoformat()

# ===============================================================
# GLOBAL KAFKA PRODUCER (REUSED FOR ALL PIPELINES)
# ===============================================================
def create_kafka_producer(broker, retries=20, delay=5):
    for i in range(retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=[broker],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            print(f"✅ Connected to Kafka at {broker}")
            return producer
        except Exception as e:
            print(f"⚠️ Kafka not ready ({e}), retrying in {delay}s... ({i+1}/{retries})")
            time.sleep(delay)

    print("❌ Failed to connect to Kafka")
    sys.exit(1)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "172.17.0.1:29092")
producer = create_kafka_producer(KAFKA_BROKER)

# ===============================================================
# PIPELINE FUNCTION
# ===============================================================
def run_pipeline(VIDEO_PATH):

    print(f"\n🚀 START PIPELINE for: {VIDEO_PATH}\n")

    video_name = os.path.splitext(os.path.basename(VIDEO_PATH))[0]
    timestamp  = now_vn().replace(":", "-")

    LOG_DIR = "/ds-app/src/output"
    os.makedirs(LOG_DIR, exist_ok=True)

    LOG_PATH = os.path.join(LOG_DIR, f"{video_name}_{timestamp}.log")

    VIDEO_TOPIC = video_name.replace(" ", "_").lower()

    CAM_ID = os.getenv("CAM_ID", "cam_auto")
    VIDEO_URL = VIDEO_PATH

    EXTRA_INFO = {
        "recordingId": f"rec_{now_vn()}",
        "cameraCode": CAM_ID,
        "path": VIDEO_PATH,
        "duration": 60.0,
        "startTime": now_vn(),
        "endTime": (datetime.now(VN_TZ) + timedelta(seconds=60)).isoformat(),
    }

    # ===============================================================
    # PROBE
    # ===============================================================
    def osd_sink_pad_buffer_probe(pad, info, u_data):
        buf = info.get_buffer()
        if not buf:
            return Gst.PadProbeReturn.OK

        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buf))
        if not batch_meta:
            return Gst.PadProbeReturn.OK

        frame_list = batch_meta.frame_meta_list
        while frame_list:
            frame_meta = pyds.NvDsFrameMeta.cast(frame_list.data)
            obj_list = frame_meta.obj_meta_list

            detections = []

            while obj_list:
                obj_meta = pyds.NvDsObjectMeta.cast(obj_list.data)

                age_label = "unknown"
                age_conf = 0.0
                phone_label = "unknown"
                phone_conf = 0.0

                cls_list = obj_meta.classifier_meta_list
                while cls_list:
                    cls_meta = pyds.NvDsClassifierMeta.cast(cls_list.data)

                    lab_list = cls_meta.label_info_list
                    while lab_list:
                        label_info = pyds.NvDsLabelInfo.cast(lab_list.data)
                        raw_label = label_info.result_label
                        label_str = pyds.get_string(raw_label) if isinstance(raw_label, int) else raw_label
                        prob = float(label_info.result_prob)

                        if label_str == "age":
                            age_label = "adult" if label_info.result_class_id == 0 else "child"
                            age_conf  = prob
                        elif label_str == "phone":
                            phone_label = "not_use_phone" if label_info.result_class_id == 0 else "use_phone"
                            phone_conf  = prob

                        lab_list = lab_list.next
                    cls_list = cls_list.next

                x1 = float(obj_meta.rect_params.left)
                y1 = float(obj_meta.rect_params.top)
                x2 = x1 + float(obj_meta.rect_params.width)
                y2 = y1 + float(obj_meta.rect_params.height)

                vn_time = now_vn()

                detections.append({
                    "xyxy": [x1, y1, x2, y2],
                    "confidence": float(obj_meta.confidence),
                    "class_id": int(obj_meta.class_id),
                    "class_name": getattr(obj_meta, "obj_label", f"class_{obj_meta.class_id}"),
                    "detect_time": vn_time,
                    "video_url": VIDEO_URL,
                    "cam_id": CAM_ID,
                    "frame_id": int(frame_meta.frame_num),
                    "push_time": vn_time,
                    "age_label": age_label,
                    "age_conf": age_conf,
                    "phone_label": phone_label,
                    "phone_conf": phone_conf,
                    "model_name": "yolo_dinov2",
                    "model_id": 1,
                    "unique_component_id": 1
                })

                obj_list = obj_list.next

            msg = {
                "cam_id": CAM_ID,
                "frame_id": int(frame_meta.frame_num),
                "detections": detections,
                "video_url": VIDEO_URL,
                "push_time": now_vn(),
                "extra_information": EXTRA_INFO,
            }

            try:
                producer.send(VIDEO_TOPIC, msg)
                producer.flush()
                print(f"📡 Sent → {VIDEO_TOPIC}")
            except Exception as e:
                print("❌ Kafka send error:", e)

            with open(LOG_PATH, "a") as f:
                f.write(json.dumps(msg) + "\n")

            frame_list = frame_list.next

        return Gst.PadProbeReturn.OK

    # ===============================================================
    # BUILD PIPELINE
    # ===============================================================
    pipeline = Gst.Pipeline.new("deepstream-pipeline")

    src = Gst.ElementFactory.make("filesrc", "src")
    src.set_property("location", VIDEO_PATH)

    decodebin = Gst.ElementFactory.make("decodebin", "decodebin")
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "nvvidconv")

    capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
    capsfilter.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM),format=NV12"))

    streammux = Gst.ElementFactory.make("nvstreammux", "streammux")
    streammux.set_property("batch-size", 1)
    streammux.set_property("width", 640)
    streammux.set_property("height", 640)
    streammux.set_property("batched-push-timeout", 40000)

    infer = Gst.ElementFactory.make("nvinfer", "primary-infer")
    infer.set_property("config-file-path", "/ds-app/configs/karter/pgies/deepstream_yolov11_config.txt")

    infer2 = Gst.ElementFactory.make("nvinfer", "secondary-infer")
    infer2.set_property("config-file-path", "/ds-app/configs/karter/sgies/config_infer_secondary_dinov2_multitask.txt")

    osd = Gst.ElementFactory.make("nvdsosd", "osd")
    sink = Gst.ElementFactory.make("fakesink", "sink")
    sink.set_property("sync", False)

    for elem in [src, decodebin, nvvidconv, capsfilter, streammux, infer, infer2, osd, sink]:
        pipeline.add(elem)

    src.link(decodebin)

    def on_pad_added(db, pad):
        sink_pad = nvvidconv.get_static_pad("sink")
        if not sink_pad.is_linked():
            pad.link(sink_pad)

    decodebin.connect("pad-added", on_pad_added)

    nvvidconv.link(capsfilter)

    srcpad = capsfilter.get_static_pad("src")
    sinkpad = streammux.get_request_pad("sink_0")
    srcpad.link(sinkpad)

    streammux.link(infer)
    infer.link(infer2)
    infer2.link(osd)
    osd.link(sink)

    pad_probe = infer2.get_static_pad("src")
    pad_probe.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, None)

    # ===============================================================
    # RUN PIPELINE
    # ===============================================================
    pipeline.set_state(Gst.State.PLAYING)
    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()

    def bus_call(bus, message, loop):
        if message.type == Gst.MessageType.EOS:
            print("🔚 End of stream")
            loop.quit()
        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("❌ GStreamer Error:", err, debug)
            loop.quit()
        return True

    bus.connect("message", bus_call, loop)

    try:
        loop.run()
    except KeyboardInterrupt:
        print("🛑 Stop by user")
    finally:
        pipeline.set_state(Gst.State.NULL)
        print(f"✅ FINISHED: {VIDEO_PATH}\n📄 Log saved at: {LOG_PATH}\n")
