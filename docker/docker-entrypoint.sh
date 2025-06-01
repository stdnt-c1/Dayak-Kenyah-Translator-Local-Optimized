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
if [ -f "vercel-deployment/api/translate.py" ]; then
    echo "Starting server from vercel-deployment..."
    cd vercel-deployment/api
    exec uvicorn translate:app --host 0.0.0.0 --port ${PORT:-8000}
else
    echo "Starting server from root..."
    exec python3 main.py
fi
