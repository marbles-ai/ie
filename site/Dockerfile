# Using this docker image: https://github.com/tiangolo/uwsgi-nginx-flask-docker
FROM tiangolo/uwsgi-nginx-flask:flask-index

ADD requirements.txt .

RUN pip install -r requirements.txt

# Set up AWS
# RUN mkdir ~/.aws && mv aws/website_config ~/.aws/config && mv aws/website_credentials ~/.aws/credentials

# Make port 5000 available to the world outside this container
# EXPOSE 5000

COPY ./app /app
