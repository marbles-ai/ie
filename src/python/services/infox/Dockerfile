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
ADD awslogs.conf /Infox
ADD build/AgentDependencies.tar.gz /Infox
ADD build/awslogs-agent-setup.py /Infox

RUN apt-get update \
    && apt-get install -y gcc apt-utils anacron libfontconfig \
    && apt-get install -y python2.7 python-pip

RUN apt-get update
RUN apt-get install -y openjdk-8-jdk

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install marbles_std-0.1-py2.py3-none-any.whl

RUN python awslogs-agent-setup.py --region=us-west-1 --dependency-path=AgentDependencies --configfile=awslogs.conf -n

# This is useful if you want to debug the container and mount ~/.aws here
# docker run -v ~/.aws:/root/.aws ...
RUN mkdir -p /root/.aws

# Set AWS Environmental variables
ENV AWS_ACCESS_KEY_ID=AKIAJ273EGWTPFTL5NXA
ENV AWS_SECRET_ACCESS_KEY=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
ENV AWS_DEFAULT_REGION=us-west-1

# This is the command to be executed when done creating our container
CMD ["./mservice.sh", "./infox.py", "start", "-j", "easysrl-0.1.0-capsule.jar", "-m", "model"]
