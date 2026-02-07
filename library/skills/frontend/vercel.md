---
name: vercel
description: "serverless frontend"
grade: B
pros: [easy to use, fast deployment]
cons: [to edit config file ]
---

# vercel

## Best Practice
(Describe the best practice pattern here)

## Snippet
```bash
# Installation and Update
pnpm i -g vercel@latest

# Authentication
# Use --token [token] in CI/CD environments
vercel login

# Project Initialization and Linking
vercel init
vercel link
```
# Development and Deployment
vercel dev --port 3000
vercel deploy --prod

# Environment and Data Management
vercel env pull .env
vercel blob list
vercel cache purge

# Project Maintenance
vercel logs [deployment-url] --follow
vercel rollback
vercel whoami
```
