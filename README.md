# 🚀 DeepStream Application Setup Guide

## 🛠️ Setup

### 1. Clone Ultralytics Repository

```bash
git clone https://github.com/ultralytics/ultralytics
```

### 2. Clone DeepStream-Yolo Repository

```bash
git clone https://github.com/marcoslucianops/DeepStream-Yolo
```

### 3. Copy YOLOv8 Export Script

```bash
cp DeepStream-Yolo/utils/export_yoloV8.py ultralytics/
```

### 4. Download YOLOv8s Model

```bash
cd ultralytics
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt
```

### 5. Convert `.pt` to `.onnx`

Pull the required Docker image:

```bash
docker pull ultralytics/ultralytics:latest
```

Run the Docker container for conversion:

```bash
docker run --rm -it -v ./:/ws -w /ws ultralytics/ultralytics:latest
```

Inside the container, install ONNX and manage PyTorch dependencies:

```bash
pip3 install onnx
pip uninstall -y torch torchvision torchaudio
```

Run the export script:

```bash
python3 export_yolov8_deepstream.py -w yolov8s.pt -s 640 --opset 17
```

### 6. Convert `.onnx` to TensorRT `.engine`

Run the DeepStream Docker container (adjust the path `/home/admin2/deep-stream` as needed):

```bash
docker run -it --gpus all --runtime=nvidia \
-v /home/admin2/deep-stream:/deep-stream \
nvcr.io/nvidia/deepstream:8.0-triton-multiarch
```

Inside the container, build the TensorRT engine:

```bash
/usr/src/tensorrt/bin/trtexec --onnx=yolov8s.onnx --fp16 --saveEngine=yolov8s.engine
```

### 7. Convert Dinov2 Multi-task Classification Model

* Convert `.pth` model to `.onnx` using:

```bash
utils/export_onnx.py
```

* Convert `.onnx` model to `.engine`.

* Build the shared object file `.so`:

```bash
nvdsinfe_custom_par_dinov2/nvdsinfer_customparser.cpp
```

## ▶️ Run the Application

### Start Zookeeper Service

```bash
docker compose up --build zookeeper -d
```

### Start Kafka Service

```bash
docker compose up --build kafka -d
```

### Start DeepStream Application Service

```bash
docker compose up --build ds-app -d
```

## 💡 Tools / Helper Scripts

* **Send Video Request:**
  Run the `request.py` file to send video processing requests:

```bash
python3 request.py
```

* **View Kafka Messages:**
  Run the `app/consumer.py` file to view Kafka messages:

```bash
python3 app/consumer.py
```
