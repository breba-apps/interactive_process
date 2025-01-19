FROM python:3.9-slim

# Install pipx from the apt repository
RUN apt-get update && \
    apt-get install -y --no-install-recommends pipx

# Add pipx’s bin directory to PATH
ENV PATH="/root/.local/bin:$PATH"

# Initialize pipx and install Poetry
RUN pipx ensurepath && \
    pipx install poetry

# Create and set the working directory
RUN mkdir -p /usr/src/interactive-process
WORKDIR /usr/src/interactive-process

# Default to a bash shell (interactive container)
CMD ["/bin/bash"]