#	Generic Dockerfile for all services
#	Based on python slim version 2.7.13

# Use an official Python runtime as a base image
FROM ubuntu:16.04

# Set the working directory where CMD will be run
WORKDIR /Ccg

# Installation stuff
ADD build/marbles_std-0.1-py2.py3-none-any.whl /Ccg
ADD requirements.txt /Ccg

# Application stuff
ADD ccgparser.py /Ccg
ADD build/easysrl-0.1.0-capsule.jar /Ccg
ADD build/model.tar.gz /Ccg
ADD build/mservice.sh /Ccg
ADD build/cp_env_credentials_to_awslogs.sh /Ccg
ADD awslogs.conf /Ccg
ADD build/AgentDependencies.tar.gz /Ccg
ADD build/awslogs-agent-setup.py /Ccg

RUN apt-get update \
    && apt-get install -y gcc apt-utils anacron libfontconfig \
    && apt-get install -y python2.7 python-pip

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install marbles_std-0.1-py2.py3-none-any.whl

RUN python awslogs-agent-setup.py --region=us-west-1 --dependency-path=AgentDependencies --configfile=awslogs.conf -n

# This is useful if you want to debug the container and mount ~/.aws here
# docker run -v ~/.aws:/root/.aws ...
RUN mkdir -p /root/.aws

# This is the command to be executed when done creating our container
CMD ["./mservice.sh", "./ccgparser.py", "start", "-j", "easysrl-0.1.0-capsule.jar", "-m", "model", "default-queue"]
