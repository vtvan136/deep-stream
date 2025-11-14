import torch
from model import MultiTaskDINOv2

def export_onnx(weight_path, onnx_path="dinov2_multitask.onnx"):
    DEVICE = "cpu"

    model = MultiTaskDINOv2()
    model.load_state_dict(torch.load(weight_path, map_location="cpu"))
    model.eval()

    dummy = torch.randn(1, 3, 224, 224)

    torch.onnx.export(
        model,
        dummy,
        onnx_path,
        input_names=["input"],
        output_names=["age_logits", "phone_logits"],
        opset_version=17,
        dynamic_axes={
            "input": {0: "batch"},
            "age_logits": {0: "batch"},
            "phone_logits": {0: "batch"}
        }
    )

    print("✅ Exported:", onnx_path)

export_onnx("/models/checkpoint_epoch_5.pth")
