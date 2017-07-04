# Using this docker image: https://github.com/tiangolo/uwsgi-nginx-flask-docker
FROM tiangolo/uwsgi-nginx-flask:flask-index

ADD requirements.txt .
ADD build/marbles_min-0.1-py2.py3-none-any.whl .
RUN pip install -r requirements.txt
RUN pip install marbles_min-0.1-py2.py3-none-any.whl
RUN pip install watchtower

# Set up AWS
# RUN mkdir ~/.aws && mv aws/website_config ~/.aws/config && mv aws/website_credentials ~/.aws/credentials

# Make port 80 available to the world outside this container
# EXPOSE 80 

COPY ./app /app
# CMD ["python", "main.py"]
