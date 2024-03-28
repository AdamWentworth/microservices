# Use an official Ubuntu base image
FROM ubuntu:20.04

# Set maintainer label
LABEL maintainer="adamjohnwentworth@gmail.com"

# Avoid prompts from apt
ARG DEBIAN_FRONTEND=noninteractive

# Install Python, Pip, and other necessary tools
RUN apt-get update -y && \
    apt-get install -y python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY . .

# Command to run the application
CMD ["python3", "app.py"]
