# Dayak Kenyah Translator Pro

<div align="center">
    <img src="images/icon.png" alt="Dayak Kenyah Translator Logo" width="200"/>
    <h3>Preserving Dayak Kenyah Language Through Modern Technology</h3>
</div>

## 🌟 About the Project

Dayak Kenyah Translator Pro is a bi-directional translation application between Indonesian and Dayak Kenyah languages. This project aims to preserve local languages through modern technology and make the Dayak Kenyah language more accessible to younger generations.

### ✨ Key Features

- 🔄 Bi-directional translation (Indonesian ↔ Dayak Kenyah)
- 💡 Smart multi-word matching
- 🌙 Dark/Light Mode
- 📱 Responsive on all devices
- ⚡ High performance with local processing
- 🔌 Available in ESP32 and Local Host versions

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Node.js 14+
- Docker (optional)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/dayak-kenyah-translator-pro.git
cd dayak-kenyah-translator-pro

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Using Docker

This application supports deployment using Docker with two options: CPU-only and GPU-accelerated (CUDA). Choose the mode that matches your hardware.

#### Prerequisites for GPU Mode
- [NVIDIA GPU Driver](https://www.nvidia.com/Download/index.aspx)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- Docker with GPU support

#### Build Image

```bash
# Build for CPU (default)
docker build -t dayak-translator .

# Build for GPU/CUDA
docker build --build-arg USE_CUDA=1 -t dayak-translator-gpu .
```

#### Running the Container

```bash
# Run CPU version
docker run -d --name dayak-translator -p 8000:8000 dayak-translator

# Run GPU version
docker run -d --name dayak-translator-gpu --gpus all -p 8000:8000 dayak-translator-gpu
```

#### Docker Features

- 🔄 Auto-detection of GPU/CPU mode
- 🛡️ Security-enhanced with non-root user
- 🏗️ Multi-stage build for optimal image size
- 🔍 Built-in health check
- 📊 Environment variable customization

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Web application port | 8000 |
| `USE_CUDA` | Enable/disable GPU acceleration | 0 (CPU) or 1 (GPU) |
| `PYTHONUNBUFFERED` | Python output buffering | 1 |

#### Monitoring Container

```bash
# Check container status
docker ps -a

# View logs
docker logs dayak-translator

# Check resource usage
docker stats dayak-translator
```

#### Troubleshooting

1. GPU Mode
```bash
# Verify GPU detection
docker run --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

2. Container Logs
```bash
# View detailed logs
docker logs -f dayak-translator
```

3. Health Check
```bash
# Check container and health status
docker inspect dayak-translator | grep -i health
```

## 🛠️ Technologies

- Python (Backend)
- HTML5, CSS3, JavaScript (Frontend)
- Docker
- ESP32 (for embedded version)

## 📖 API Documentation

### Main Endpoint

- `POST /translate`
  - Body: `{"text": "text to translate", "direction": "id2dyk|dyk2id"}`
  - Response: `{"result": "translated text"}`

## 🤝 Contributing

Contributions are always welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👏 Acknowledgments

This project is developed from:
- [Dayak Kenyah Translator ESP32](https://github.com/RyuHiiragi/Dayak-Kenyah-Translator-ESP-32.git) by Muhammad Rizky Saputra
- [Dayak Kenyah Translator Local](https://github.com/stdnt-c1/Dayak-Kenyah-Translator-Local-Optimized.git) by Muhammad Bilal Maulida
