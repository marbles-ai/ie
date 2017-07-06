# Using this docker image: https://github.com/tiangolo/uwsgi-nginx-flask-docker
FROM tiangolo/uwsgi-nginx-flask:flask-index

ADD requirements.txt .
ADD build/marbles_min-0.1-py2.py3-none-any.whl .
RUN pip install -r requirements.txt
RUN pip install marbles_min-0.1-py2.py3-none-any.whl
RUN pip install watchtower

COPY ./app /app
