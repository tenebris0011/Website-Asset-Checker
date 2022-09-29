FROM python:3.8
RUN mkdir -p /app/logs
RUN mkdir -p /app/resources
COPY main.py /app/main.py
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN apt-get update -y \
    && apt-get install -y wget \
    && wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt install ./google-chrome-stable_current_amd64.deb -y \
    && wget https://bootstrap.pypa.io/get-pip.py \
    && python3 get-pip.py \
    && rm get-pip.py \
    && pip install -r requirements.txt
CMD ["python", "main.py"]
