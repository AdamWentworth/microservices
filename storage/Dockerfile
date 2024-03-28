# Start from the Ubuntu base image
FROM ubuntu:20.04

# Set the maintainer label
LABEL maintainer="adamjohnwentworth@gmail.com"

# Avoid interactive prompts during the build
ARG DEBIAN_FRONTEND=noninteractive

# Install Python, pip, and MySQL client
RUN apt-get update -y && \
    apt-get install -y python3 python3-pip libmysqlclient-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container to /app
WORKDIR /app

# Copy the Python dependencies file to the container
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code to the container
COPY . .

# Expose the port the app runs on
EXPOSE 8090

# Define the entrypoint as bash to handle the init process and threading properly
ENTRYPOINT [ "/bin/bash", "-c" ]

# Specify the command to run on container start
CMD ["exec python3 -m app"]
