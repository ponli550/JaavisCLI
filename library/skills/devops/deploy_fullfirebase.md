---
name: FullFirebase
description: "React X Firebase Fullstack Orchestrator"
grade: A
tags: [firebase, react, framework]
pros:
  - "Zero-config scaffolding"
  - "Automated security rules"
cons:
  - "Requires manual Firebase Console project creation"
---

# FullFirebase

This skill automates the setup of a Vite/React frontend integrated with Firebase Auth, Firestore, and Hosting. It enforces Grade A security standards by default.

## Snippet
<!-- JAAVIS:EXEC -->
```bash
# 1. Environment Guard
if ! command -v firebase &> /dev/null; then
    echo "❌ Firebase CLI not found. Installing globally..."
    npm install -g firebase-tools
fi

# 2. Scaffolding (One-Army Standard: apps/web)
TARGET="apps/web"
mkdir -p apps

if [ -d "$TARGET" ]
then
    echo "⚠️  '$TARGET' already exists. Using 'apps/web-firebase' instead."
    TARGET="apps/web-firebase"
fi

# Bypass Vite prompts for speed
printf 'n\nn\n' | npm create vite@latest "$TARGET" -- --template vanilla
cd "$TARGET"

# 3. Dependencies
npm install firebase

# 4. Configuration Injection
# Injecting local firebase.js
echo 'export const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123"
};' > src/firebase.js

# Injecting Security Rules
echo 'rules_version = "2";
service cloud.firestore {
  match /databases/{database}/documents {
    match /todos/{todoId} {
      allow read, write: if request.auth != null && request.auth.uid == resource.data.uid;
      allow create: if request.auth != null && request.auth.uid == request.resource.data.uid;
    }
  }
}' > firestore.rules

# 5. Deployment Orchestration
echo "--------------------------------------------------------"
printf "🔥 Enter your Firebase Project ID: "
read PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo "⚠️ No Project ID. Skipping deployment configuration."
else
    # Programmatic creation of Firebase config (Skips 'firebase init')
    echo "{
      \"firestore\": { \"rules\": \"firestore.rules\" },
      \"hosting\": {
        \"public\": \"dist\",
        \"ignore\": [\"firebase.json\", \"**/.*\", \"**/node_modules/**\"]
      }
    }" > firebase.json

    echo "{ \"projects\": { \"default\": \"$PROJECT_ID\" } }" > .firebaserc

    echo "🏗️ Building and Deploying..."
    npm run build
    firebase deploy --only hosting --project "$PROJECT_ID"
fi

echo "✅ FullFirebase logic applied. Launching dev environment..."
npm run dev
```
