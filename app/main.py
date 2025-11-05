import sys, os
import gi
import pyds

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

# --- Tham số --
VIDEO_PATH = None
if "--video" in sys.argv:
    VIDEO_PATH = sys.argv[sys.argv.index("--video") + 1]
else:
    print("Usage: python3 script.py --video <path_to_video>")
    sys.exit(1)

OUTPUT_PATH = "/output/results.txt"

def osd_sink_pad_buffer_probe(pad, info, u_data):
    buf = info.get_buffer()
    if not buf:
        return Gst.PadProbeReturn.OK

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buf))
    if not batch_meta:
        return Gst.PadProbeReturn.OK

    l_frame = batch_meta.frame_meta_list
    results = []

    while l_frame is not None:
        frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        l_obj = frame_meta.obj_meta_list
        while l_obj is not None:
            obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            results.append(
                f"{frame_meta.frame_num},{obj_meta.class_id},"
                f"{obj_meta.confidence:.2f},"
                f"{obj_meta.rect_params.left:.1f},"
                f"{obj_meta.rect_params.top:.1f},"
                f"{obj_meta.rect_params.width:.1f},"
                f"{obj_meta.rect_params.height:.1f}"
            )
            l_obj = l_obj.next
        l_frame = l_frame.next

    if results:
        with open(OUTPUT_PATH, "a") as f:
            f.write("\n".join(results) + "\n")

    return Gst.PadProbeReturn.OK

def main():
    pipeline = Gst.Pipeline()

    # Source
    src = Gst.ElementFactory.make("filesrc", "src")
    src.set_property("location", VIDEO_PATH)

    decodebin = Gst.ElementFactory.make("decodebin", "decodebin")
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "nvvidconv")
    capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
    capsfilter.set_property(
        "caps",
        Gst.Caps.from_string("video/x-raw(memory:NVMM), format=NV12")
    )

    streammux = Gst.ElementFactory.make("nvstreammux", "streammux")
    streammux.set_property("batch-size", 1)
    streammux.set_property("width", 640)
    streammux.set_property("height", 640)
    streammux.set_property("batched-push-timeout", 40000)

    infer = Gst.ElementFactory.make("nvinfer", "primary-infer")
    # Cập nhật đường dẫn đến file config của bạn
    infer.set_property("config-file-path", "/configs/deepstream_yolov8_config.txt")

    osd = Gst.ElementFactory.make("nvdsosd", "osd")
    sink = Gst.ElementFactory.make("fakesink", "sink")
    sink.set_property("sync", False)

    # Thêm tất cả elements
    for elem in [src, decodebin, nvvidconv, capsfilter, streammux, infer, osd, sink]:
        if not elem:
            print("❌ Failed to create one of the elements")
            sys.exit(1)
        pipeline.add(elem)

    # Link filesrc → decodebin
    src.link(decodebin)

    # dynamic pad linking for decodebin → nvvidconv
    def on_pad_added(decodebin, pad):
        print("🔗 New pad added from decodebin:", pad.get_name())
        sink_pad = nvvidconv.get_static_pad("sink")
        if not sink_pad.is_linked():
            pad.link(sink_pad)

    decodebin.connect("pad-added", on_pad_added)

    # Link nvvidconv → capsfilter → streammux
    nvvidconv.link(capsfilter)
    capsfilter_src_pad = capsfilter.get_static_pad("src")
    streammux_sink_pad = streammux.get_request_pad("sink_0")
    if not capsfilter_src_pad.link(streammux_sink_pad) == Gst.PadLinkReturn.OK:
        print("❌ Failed to link capsfilter → streammux")
        sys.exit(1)

    # Link streammux → infer → osd → sink
    streammux.link(infer)
    infer.link(osd)
    osd.link(sink)

    # Attach probe at infer src pad
    infer_src_pad = infer.get_static_pad("src")
    if not infer_src_pad:
        print("❌ Unable to get src pad from nvinfer")
        sys.exit(1)
    infer_src_pad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, None)

    print("🚀 Running pipeline...")
    pipeline.set_state(Gst.State.PLAYING)

    bus = pipeline.get_bus()
    while True:
        msg = bus.timed_pop_filtered(1000, Gst.MessageType.EOS | Gst.MessageType.ERROR)
        if msg:
            if msg.type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                print(f"❌ Error: {err}, {debug}")
            break

    pipeline.set_state(Gst.State.NULL)
    print("✅ Done. Results saved at:", OUTPUT_PATH)

if __name__ == "__main__":
    main()

