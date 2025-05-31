#!/bin/bash

# Function to check CUDA availability
check_cuda() {
    if [ "${USE_CUDA}" = "1" ]; then
        if command -v nvidia-smi &> /dev/null; then
            echo "CUDA support detected and enabled"
            return 0
        else
            echo "Warning: CUDA was requested but no GPU detected. Falling back to CPU mode."
            return 1
        fi
    fi
    return 1
}

# Initialize environment based on hardware
if check_cuda; then
    export CUDA_VISIBLE_DEVICES=0
    export USE_GPU=1
else
    export CUDA_VISIBLE_DEVICES=""
    export USE_GPU=0
fi

# Start the application
if [ -f "webroot/server/main.py" ]; then
    echo "Starting server from webroot..."
    exec python3 webroot/server/main.py
else
    echo "Starting server from root..."
    exec python3 main.py
fi
