# Use an official Python runtime as a base image
FROM python:2.7-slim

# Set the working directory to /app
WORKDIR /webapp

# Copy the current directory contents into the container at /webapp
ADD . /webapp

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000 

# Define environment variable
ENV HOME /webapp

# Run app.py when the container launches
CMD ["python", "run.py"]
