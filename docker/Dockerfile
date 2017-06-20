#	Generic Dockerfile for all services
#	Based on python slim version 2.7.13

# Use an official Python runtime as a base image
FROM ubuntu:16.04

# Set the working directory where CMD will be run
WORKDIR /Newsreader

# Copy applications folder into our container
ADD docker/requirements.txt /Newsreader
ADD src/python /Newsreader/src
ADD scripts /Newsreader/scripts

RUN apt-get update \
    && apt-get install -y gcc apt-utils\
    && apt-get install -y python2.7 python-pip

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt 

# Install marbles!
RUN cd src && python setup.py install

# Set all the correct env variables for the build script
ENV PYTHON_VERSION 2.7 
ENV PYTHON_BUILD 13

# This is the command to be executed when done creating our container
CMD ["scripts/mservice.sh", "src/services/newsreader/newsreader.py", "start", "default-queue"]
