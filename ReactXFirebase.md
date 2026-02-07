/* Step 1: Scaffold Project
npx create vite@latest web-firebase-todo -- --template vanilla
npm install firebase
*/

// Step 2: Initialize Firebase (src/firebase.js)
export const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123",
};

// Step 3: Firestore Security Rules
/*
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /todos/{todoId} {
      allow read, write: if request.auth != null && request.auth.uid == resource.data.uid;
      allow create: if request.auth != null && request.auth.uid == request.resource.data.uid;
    }
  }
}
*/

// Step 4: AI Summarization Logic (src/main.js)
import { getAI, getGenerativeModel, GoogleAIBackend } from "firebase/ai";
const ai = getAI(app, { backend: new GoogleAIBackend() });
const model = getGenerativeModel(ai, { model: "gemini-2.0-flash" });

summarizeBtn.addEventListener("click", async () => {
  const prompt = `Summarize this todo list: ${currentTodos.map(t => t.text).join(", ")}`;
  const result = await model.generateContent(prompt);
  summaryBox.textContent = result.response.text();
});

/*
Step 5: Deploy
npm run build
firebase deploy --only hosting
*/
