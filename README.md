# ds-app

- Ultralytics

` git clone https://github.com/ultralytics/ultralytics `

- Deepstream Yolo

` git clone https://github.com/marcoslucianops/DeepStream-Yolo `

- Copy file:

` cp DeepStream-Yolo/utils/export_yoloV8.py ultralytics/ `

- Download model

` cd ultralytics && wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt `

- Convert pt to onnx

` docker pull ultralytics/ultralytics:latest `
` docker run --rm -it -v ./:/ws -w /ws ultralytics/ultralytics:latest ` 
` pip3 install onnx `
` pip uninstall -y torch torchvision torchaudio `
` pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121 `
` python3 export_yolov8_deepstream.py -w yolov8s.pt -s 640 --opset 17 `

- Convert onnx to engine

` docker run -it --gpus all --runtime=nvidia \
  -v /root/DS-APP:/DS-APP \
  nvcr.io/nvidia/deepstream:7.0-triton-multiarch `
` /usr/src/tensorrt/bin/trtexec --onnx=yolov8m.onnx --fp16 --saveEngine=yolov8m.engine `


