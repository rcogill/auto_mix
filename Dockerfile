#----------------------------------------------------------------------------
#
# Dockerfile for building the auto_mix container
#
#----------------------------------------------------------------------------

FROM ubuntu:latest

RUN apt-get update

RUN apt-get install -y apt-utils
RUN apt-get install -y build-essential checkinstall
RUN apt-get install -y python3
RUN apt-get install -y python3-pip 
RUN apt-get install -y python3-dev
RUN apt-get install -y ffmpeg

RUN pip3 install --upgrade pip
RUN pip3 install pyyaml
RUN pip3 install boto3
RUN pip3 install requests
RUN pip3 install click

RUN mkdir /var/mix/

# Configuring encoding to support use of the click module
RUN export LC_ALL=C.UTF-8
RUN export LANG=C.UTF-

COPY src/ /var/mix/

