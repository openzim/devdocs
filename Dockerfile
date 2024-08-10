FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.source https://github.com/openzim/devdocs

# Install necessary packages
RUN apt-get update \
     && apt-get install -y --no-install-recommends \
     libmagic1 \
     && rm -rf /var/lib/apt/lists/* \
     && python -m pip install --no-cache-dir -U \
      pip

# Copy pyproject.toml and its dependencies
COPY pyproject.toml README.md /src/
COPY src/devdocs2zim/__about__.py /src/src/devdocs2zim/__about__.py

# Install Python dependencies
RUN pip install --no-cache-dir /src

# Copy code + associated artifacts
COPY src /src/src
COPY *.md /src/

# Install + cleanup
RUN pip install --no-cache-dir /src \
 && rm -rf /src

CMD ["devdocs2zim", "--help"]
