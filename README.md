# Image Rotation Service

A production-ready, cloud-native Flask service that rotates uploaded images entirely in-memory using the provided OCR-driven orientation logic.

## Features
- `POST /rotate` accepts `multipart/form-data` uploads with the `file` field.
- Runs the exact OCR-based rotation pipeline provided in the spec without touching disk.
- Responds with the rotated image bytes alongside clear HTTP status codes.
- Includes `/healthz` for container, Kubernetes, or load balancer probes.
- Ships with Docker, Gunicorn configuration, and Kubernetes manifests for rapid deployment.

## Getting Started

## CMD
set FLASK_APP=app/wsgi.py
flask run --host=0.0.0.0 --port=8080


### Prerequisites
- Python 3.11+
- Tesseract OCR binaries available on your system

### Local Development
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
FLASK_APP=app/wsgi.py flask run --host=0.0.0.0 --port=8080
```

### Usage
```bash
curl -X POST \
  -F "file=@/path/to/image.jpg" \
  http://localhost:8080/rotate --output rotated.jpg
```

### Testing
```bash
pytest
```

## Container Image
Build and run locally:
```bash
docker build -t iap-image-rotator .
docker run --rm -p 8080:8080 iap-image-rotator
```

The Docker image installs the Tesseract engine, the `fas` language pack, and `pytesseract` so the OCR-driven rotation routine wo
rks without any additional runtime dependencies.

## Kubernetes
Apply the sample manifests (update the image reference first):
```bash
kubectl apply -f k8s/deployment.yaml
```

The deployment defines readiness and liveness probes hitting `/healthz` and exposes the service on port 80 via a ClusterIP service.

## Configuration
| Variable | Default | Description |
| --- | --- | --- |
| `ROTATION_LANG` | `fas+eng` | Tesseract language pack codes passed to the rotation routine. |
| `ROTATION_MIN_SCORE_DIFF` | `200` | Minimum OCR score delta for trusting rotation decisions. |
| `GUNICORN_BIND` | `0.0.0.0:8080` | Bind address for Gunicorn in the container. |
| `WEB_CONCURRENCY` | `2 * CPU + 1` | Number of Gunicorn workers. |
| `GUNICORN_THREADS` | `4` | Threads per worker. |

## Security Considerations
- All image handling occurs in-memory to avoid leaking sensitive data to disk.
- Input validation returns explicit 400/415 errors for malformed requests.
- Gunicorn logs to STDOUT/STDERR for seamless aggregation by container platforms.
