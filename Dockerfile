FROM nvcr.io/nvidia/deepstream:7.0-triton-multiarch

# Cài Python và gói cơ bản
RUN apt-get update -y && apt-get install -y python3-pip \
 && pip3 install pyyaml opencv-python numpy


#RUN add-apt-repository ppa:jonathonf/ffmpeg-4 -y && apt-get update

# Cài plugin GStreamer bị thiếu (loại bỏ toàn bộ cảnh báo)
RUN apt-get update && apt-get install -y \
    libmpg123-0 \
    libmpeg2-4 \
    libmpeg2encpp-2.1-0 \
    libavcodec58 \
    libavformat58 \
    libavutil56 \
    libswresample3 \
    libswscale5 \
    libvpx7 \
    libchromaprint-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
 && rm -rf /var/lib/apt/lists/*

RUN apt-get install libmpeg2-4 libmpeg2encpp-2.1-0

RUN apt-get install libavcodec58 libavformat58 libavutil56 libswresample3 libswscale5

# Cài pyds
WORKDIR /pyds
COPY pyds-1.1.10-py3-none-linux_x86_64.whl .
RUN pip3 install ./pyds-1.1.10-py3-none-linux_x86_64.whl

# Cài cuda-python (nếu cần dùng TensorRT/PyCUDA)
RUN pip3 install cuda-python

# Copy mã nguồn DeepStream app
WORKDIR /ds_app
COPY . /ds_app

# Tùy chọn: giữ container sống để debug
CMD ["tail", "-f", "/dev/null"]

