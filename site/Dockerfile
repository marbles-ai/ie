#	Docker image for reverse-proxied Flask instance

# Using this docker image: https://github.com/tiangolo/uwsgi-nginx-flask-docker
FROM tiangolo/uwsgi-nginx-flask:flask-index

# Copy over the requirements and marbles wheel file
ADD requirements.txt .
ADD build/marbles_min-0.1-py2.py3-none-any.whl .
ADD build/cp_env_credentials_to_awslogs.sh .
ADD awslogs.conf .
ADD build/AgentDependencies.tar.gz .
ADD build/awslogs-agent-setup.py .

# Install any needed packages
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install marbles_min-0.1-py2.py3-none-any.whl
RUN pip install watchtower

# Get the aws log agent up and running
RUN python awslogs-agent-setup.py --region=us-west-1 --dependency-path=AgentDependencies --configfile=awslogs.conf -n

# Copy over the flask server code
COPY ./app /app
