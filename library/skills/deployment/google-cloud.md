---
title: Google Cloud
domain: deployment
tags: [tag1, tag2]
---

<!-- JAAVIS:EXEC -->
```bash

pip install cloud-sql-python-connector
pip install pg8000
echo "This is runnable knowledge"
```

# Google Cloud
Google Cloud SQL is a fully-managed relational database service offered by Google as part of its Google Cloud Platform (GCP). It provides users with SQL database instances that are compatible with popular database management systems.
## Best Practice
Enable Cloud SQL Admin API: APIs & Services > Library > Cloud SQL Admin API:Click Enable
Create a new PostgreSQL instances: Choose PostgreSQL
Create a new PostgreSQL instances: When requested, enable the Compute Engine API:

https://cloud.google.com/sdk/docs/install
Run Google Cloud SDK Shell and type the following command: gcloud auth application-default login
To set the application quota:
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
Run the application with uvicorn and perform the CRUD operation from swagger UI.

## Snippet
```
(Paste your code snippet here)
```
