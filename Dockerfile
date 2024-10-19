FROM ubuntu

# update
RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    openssh-client

# create ssh keys
RUN ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N ''

# app directory for our source files
WORKDIR /app

# install requirements
COPY ./requirements.txt ./requirements.txt
RUN python3 -m venv .venv
RUN ./.venv/bin/pip install -r ./requirements.txt

# copy source files
COPY src/ src/
COPY main.py main.py

CMD ["./.venv/bin/python3", "main.py"]
