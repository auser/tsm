FROM python:3.11-slim

WORKDIR /build
COPY . .

# Debug: List files and show directory structure
RUN echo "=== Directory Structure ===" && \
    find . -type f -o -type d | sort && \
    echo "=== Contents of spec/tsm.spec ===" && \
    cat spec/tsm.spec && \
    echo "=== End of spec/tsm.spec ==="

# Install system dependencies required for PyInstaller
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    binutils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install pyinstaller && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Build the binary using the spec file
RUN cd /build && \
    pyinstaller spec/tsm.spec --clean

# Debug: Show build output
RUN echo "=== Build Output ===" && \
    ls -la /build/dist/ && \
    echo "=== End Build Output ==="

# Clean up any generated spec files
RUN rm -f tsm.spec
