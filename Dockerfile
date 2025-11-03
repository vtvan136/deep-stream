FROM nvcr.io/nvidia/deepstream:7.0-triton-multiarch

RUN apt-get update -y && apt-get install -y python3-pip
RUN pip3 install pyyaml opencv-python numpy

WORKDIR /ds_app
COPY . /ds_app
