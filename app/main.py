import sys, os, time
import pyds
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

VIDEO_PATH = sys.argv[sys.argv.index("--video")+1]
OUTPUT_PATH = "/output/results.txt"

def osd_sink_pad_buffer_probe(pad, info, u_data):
    buf = info.get_buffer()
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buf))
    l_frame = batch_meta.frame_meta_list
    results = []

    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break
        frame_number = frame_meta.frame_num
        l_obj = frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            results.append(f"{frame_number},{obj_meta.class_id},{obj_meta.confidence:.2f},{obj_meta.rect_params.left:.1f},{obj_meta.rect_params.top:.1f},{obj_meta.rect_params.width:.1f},{obj_meta.rect_params.height:.1f}")
            try:
                l_obj = l_obj.next
            except StopIteration:
                break
        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    if results:
        with open(OUTPUT_PATH, "a") as f:
            for r in results:
                f.write(r + "\n")

    return Gst.PadProbeReturn.OK


def main():
    pipeline = Gst.parse_launch(
        f"filesrc location={VIDEO_PATH} ! decodebin ! nvstreammux name=mux batch-size=1 width=640 height=640 ! "
        f"nvinfer config-file-path=/configs/deepstream_yolov8_config.txt ! nvdsosd name=osd ! fakesink sync=false"
    )

    osd = pipeline.get_by_name("osd")
    osd_sink_pad = osd.get_static_pad("sink")
    osd_sink_pad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, 0)

    print("🚀 Running pipeline...")
    pipeline.set_state(Gst.State.PLAYING)
    bus = pipeline.get_bus()

    while True:
        msg = bus.timed_pop_filtered(1000, Gst.MessageType.EOS | Gst.MessageType.ERROR)
        if msg:
            break

    pipeline.set_state(Gst.State.NULL)
    print("✅ Done. Results saved at:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
