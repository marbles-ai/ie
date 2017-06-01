#	Dockerfile to build ...
#	Based on Ubuntu
#

# Set base image to ubuntu
FROM ubuntu

# Install the tools we need to run the build script
RUN  apt-get update \
  && apt-get install -y wget python-pip apt-utils virtualenv

# Set the working directory where CMD will be run
WORKDIR /vpython

# Copy applications folder into our container
ADD . /vpython

# Set all the correct env variables for the build script
# ENV PYTHON_VERSION <version>
# ENV PYTHON_BUILD <build>

# Run build script
RUN ["chmod", "+x", "build.sh"]
RUN ./build.sh

# This is the command to be executed when done creating our container
CMD "echo Hello World!"
