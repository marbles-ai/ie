#	Generic Dockerfile for all services
#	Based on python slim version 2.7.13

# Use an official Python runtime as a base image
FROM ubuntu:16.04

# Set the working directory where CMD will be run
WORKDIR /Newsreader

# Copy applications folder into our container
ADD newsreader.py /Newsreader
ADD build/marbles_std-0.1-py2.py3-none-any.whl /Newsreader
ADD build/mservice.sh /Newsreader
ADD requirements.txt /Newsreader

RUN apt-get update \
    && apt-get install -y gcc apt-utils \
    && apt-get install -y python2.7 python-pip

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt 
RUN pip install marbles_std-0.1-py2.py3-none-any.whl

# This is the command to be executed when done creating our container
CMD ["./mservice.sh", "./newsreader.py", "start", "default-queue"]
