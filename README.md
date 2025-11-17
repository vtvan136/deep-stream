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

`    `

` python3 export_yolov8_deepstream.py -w yolov8s.pt -s 640 --opset 17 `

- Convert onnx to engine

` docker run -it --gpus all --runtime=nvidia \
  -v /home/admin2/deep-stream:/deep-stream \
  nvcr.io/nvidia/deepstream:8.0-triton-multiarch `
  
` /usr/src/tensorrt/bin/trtexec --onnx=yolo11s.pt.onnx --fp16 --saveEngine=yolo11s.engine `


