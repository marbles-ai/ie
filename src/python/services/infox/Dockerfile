#	Generic Dockerfile for all services
#	Based on python slim version 2.7.13

# Use an official Python runtime as a base image
FROM ubuntu:16.04

# Set the working directory where CMD will be run
WORKDIR /Infox

# Copy applications folder into our container
ADD build/marbles_std-0.1-py2.py3-none-any.whl /Infox
ADD requirements.txt /Infox

# Application Stuff
ADD infox.py /Infox
ADD build/easysrl-0.1.0-capsule.jar /Infox
ADD build/model.tar.gz /Infox
ADD build/mservice.sh /Infox
ADD build/cp_env_credentials_to_awslogs.sh /Infox

RUN apt-get update \
    && apt-get install -y gcc apt-utils libfontconfig \
    && apt-get install -y python2.7 python-pip

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt 
RUN pip install marbles_std-0.1-py2.py3-none-any.whl

# This is the command to be executed when done creating our container
CMD ["./mservice.sh", "./infox.py", "start", "-j", "easysrl-0.1.0-capsule.jar", "-m", "model"]
