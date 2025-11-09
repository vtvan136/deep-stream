FROM nvcr.io/nvidia/deepstream:7.0-triton-multiarch

ENV NVIDIA_DRIVER_CAPABILITIES $NVIDIA_DRIVER_CAPABILITIES,video
ENV LOGLEVEL="INFO"
ENV GST_DEBUG=2
ENV GST_DEBUG_FILE=/ds-app/GST_DEBUG.log
ENV CUDA_VER=12

RUN apt update -y && apt-get -y install \
    libgstrtspserver-1.0-dev \
    gstreamer1.0-rtsp \
    libapr1 \
    libapr1-dev \
    libaprutil1 \
    libaprutil1-dev \
    libgeos-dev \
    libcurl4-openssl-dev python3-pip \
    graphviz \
    libcairo2-dev pkg-config python3-dev \
    libgirepository1.0-dev

RUN apt-get -y install \
    libavformat-dev \
    libswscale-dev  

RUN cp /usr/local/cuda-${CUDA_VER}/targets/x86_64-linux/lib/stubs/libcuda.so /usr/local/lib/

# RUN apt -y install libapr*
RUN python3 -m pip install --upgrade pip
COPY ds.requirements requirements.txt
RUN pip3 install -r requirements.txt

## For Pyds
RUN apt-get -y install \
    libcairo2-dev \
    pkg-config python3-dev \
    libgirepository1.0-dev

# Install pyds
#WORKDIR 
COPY pyds-1.1.10-py3-none-linux_x86_64.whl .
RUN pip3 install ./pyds-1.1.10-py3-none-linux_x86_64.whl

RUN pip install kafka-python

# Build all custom infer plugins under each subfolder of ds_app/nvdsinfer_custom
# WORKDIR /nvdsinfer_custom
# COPY ds_app/nvdsinfer_custom .
# RUN for d in *; do \
#       if [ -d "$d" ]; then \
#         for sub in "$d"/*; do \
#           if [ -d "$sub" ]; then \
#             sub_name=$(basename "$sub"); \
#             parent_name=$(basename "$d"); \
#             mkdir -p /$parent_name/$sub_name; \
#             cp -r "$sub"/. /$parent_name/$sub_name; \
#             cd /$parent_name/$sub_name; \
#             make clean && make -j4; \
#             cd /nvdsinfer_custom; \
#           fi; \
#         done; \
#       fi; \
#     done

# Build dsl
# WORKDIR /dsl
# COPY ./ds_app/dsl .
#RUN make clean && make -j4 && make install

RUN apt update && apt install wget -y && rm -rf /var/lib/apt/lists/*

RUN pip3 install cuda-python

#COPY ./build/ds_config/production /configs

COPY ./ ./ds-app 

WORKDIR /ds-app

