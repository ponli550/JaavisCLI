---
name: Docker Compose (Flask)
description: "Containerized Flask API with Redis"
grade: B
tags: [backend, docker, python]
pros:
  - "Portable & Consistent"
  - "Easy to scale"
cons:
  - "Heavier resource usage than bare metal"
---
# Deployment: Docker Compose Quickstart
> Harvested on 2026-02-06
> Source: Docker Documentation

## Execution Plan
<!-- JAAVIS:EXEC -->
```bash
mkdir -p {{target_dir}}
python3 -c "import os; open('{{target_dir}}/app.py', 'w').write(\"import time\nimport redis\nfrom flask import Flask\n\napp = Flask(__name__)\ncache = redis.Redis(host='redis', port=6379)\n\ndef get_hit_count():\n    retries = 5\n    while True:\n        try:\n            return cache.incr('hits')\n        except redis.exceptions.ConnectionError as exc:\n            if retries == 0:\n                raise exc\n            retries -= 1\n            time.sleep(0.5)\n\n@app.route('/')\ndef hello():\n    count = get_hit_count()\n    return f'Hello World! I have been seen {count} times.'\")"
python3 -c "open('{{target_dir}}/requirements.txt', 'w').write('flask\nredis')"
python3 -c "open('{{target_dir}}/Dockerfile', 'w').write('# syntax=docker/dockerfile:1\nFROM python:3.10-alpine\nWORKDIR /code\nENV FLASK_APP=app.py\nENV FLASK_RUN_HOST=0.0.0.0\nRUN apk add --no-cache gcc musl-dev linux-headers\nCOPY requirements.txt requirements.txt\nRUN pip install -r requirements.txt\nEXPOSE 5000\nCOPY . .\nCMD [\"flask\", \"run\", \"--debug\"]')"
python3 -c "open('{{target_dir}}/compose.yaml', 'w').write('services:\n  web:\n    build: .\n    ports:\n      - \"8000:5000\"\n  redis:\n    image: \"redis:alpine\"')"
echo "✅ Scaffolded '{{target_dir}}' directory."
echo "👉 Run: cd {{target_dir}} && docker compose up"
```

## Tutorial Content

This tutorial aims to introduce fundamental concepts of Docker Compose by guiding you through the development of a basic Python web application.

Using the Flask framework, the application features a hit counter in Redis, providing a practical example of how Docker Compose can be applied in web development scenarios.

### Step 1: Set up
The execution plan above automatically creates the `composetest` directory and the necessary files:
- `app.py`
- `requirements.txt`
- `Dockerfile`
- `compose.yaml`

### Step 2: Build and run your app with Compose
From your project directory, start up your application by running docker compose up.

```bash
cd composetest
docker compose up
```

Enter http://localhost:8000/ in a browser to see the application running.
