# Use an official Ubuntu base image
FROM ubuntu:20.04

# Set maintainer label
LABEL maintainer="adamjohnwentworth@gmail.com"

# Avoid prompts from apt during the build
ARG DEBIAN_FRONTEND=noninteractive

# Install Python, Pip, SQLite3, and other necessary tools
RUN apt-get update -y && \
    apt-get install -y python3 python3-pip sqlite3 && \
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

# Expose the port the app runs on
EXPOSE 8100

# Use the entrypoint to use bash (needed for init_scheduler function and APScheduler)
ENTRYPOINT [ "/bin/bash", "-c" ]

# Command to run the application, using `exec` to make sure Python runs as PID 1
CMD ["exec python3 -m app"]
