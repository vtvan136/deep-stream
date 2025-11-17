FROM nvcr.io/nvidia/deepstream:8.0-triton-multiarch

ENV NVIDIA_DRIVER_CAPABILITIES=$NVIDIA_DRIVER_CAPABILITIES,video
ENV LOGLEVEL="INFO"
ENV GST_DEBUG=2
ENV GST_DEBUG_FILE=/ds-app/GST_DEBUG.log
ENV CUDA_VER=12
ENV DEEPSTREAM_DIR=/opt/nvidia/deepstream/deepstream-8.0

# ====== Base packages ======
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
    libgirepository1.0-dev \
    libavformat-dev \
    libswscale-dev \
    libsndfile1 \
    libmp3lame0 && \
    rm -rf /var/lib/apt/lists/*

# Fix cuda runtime link stub
RUN cp /usr/local/cuda-${CUDA_VER}/targets/x86_64-linux/lib/stubs/libcuda.so /usr/local/lib/

# ====== Install Python deps ======
COPY build/ds.requirements requirements.txt 
RUN pip3 install --no-cache-dir --ignore-installed -r requirements.txt

# Fake libpython for DeepStream pyds
RUN ln -s /usr/lib/x86_64-linux-gnu/libpython3.12.so.1.0 /usr/lib/x86_64-linux-gnu/libpython3.10.so.1.0

# ====== GStreamer plugins & codec dependencies ======
RUN apt-get update && apt-get install -y \
    gstreamer1.0-libav \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    libmpg123-0 \
    libflac12 \
    libvpx9 \
    libdvdread8 \
    libdvdnav4 \
    libmjpegutils-2.1-0 \
    libdca0 \
    && rm -rf /var/lib/apt/lists/*

# ====== Optional Fix: Remove DeepStream Rivermax UDP plugin if unused ======
# Vì plugin này yêu cầu thư viện ngoài (librivermax.so.1)
RUN rm -f /usr/lib/x86_64-linux-gnu/gstreamer-1.0/deepstream/libnvdsgst_udp.so

# ====== Install PyDS & other deps ======
COPY pyds-1.2.2-cp312-cp312-linux_x86_64.whl .
RUN pip3 install ./pyds-1.2.2-cp312-cp312-linux_x86_64.whl
RUN pip3 install kafka-python-ng
RUN pip3 install cuda-python

# ====== Copy entire project to /ds-app ======
COPY . /ds-app
WORKDIR /ds-app

# ====== Build DINOv2 custom parser (nếu cần) ======
# WORKDIR /ds-app/libs
# RUN make clean && make && make install
