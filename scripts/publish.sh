#!/bin/bash
set -e

# Jaavis Release Automation
# Usage: ./scripts/publish.sh

echo "🚀 Jaavis Release Protocol"
echo "--------------------------------"

# 1. Extract Version
VERSION=$(grep 'VERSION =' jaavis_core.py | cut -d '"' -f 2)
echo "📦 Current Version: $VERSION"

# 2. Key Confirmation
read -p "❓ Proceed with release v$VERSION? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# 3. Git Check
if [[ -n $(git status -s) ]]; then
    echo "⚠️  Uncommitted changes detected."
    read -p "❓ Commit all changes as 'Release v$VERSION'? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        git commit -m "Release v$VERSION"
    else
        echo "Please commit changes first."
        exit 1
    fi
fi

# 4. Tag & Push
echo "🏷️  Tagging v$VERSION..."
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "⚠️  Tag v$VERSION already exists. Overwriting..."
    git tag -d "v$VERSION"
    git push origin :refs/tags/v$VERSION
fi

git tag "v$VERSION"
echo "⬆️  Pushing to origin..."
git push origin main
git push origin "v$VERSION"

echo "✅ Code released to GitHub."

# 5. Homebrew Update Calculation
echo "🍺 Calculating SHA256 for Homebrew..."
URL="https://github.com/ponli550/JaavisCLI/archive/refs/tags/v$VERSION.tar.gz"
echo "   Downloading $URL..."

# Wait a bit for GitHub to generate tarball
sleep 2

# Download and calc hash
SHA=$(curl -sL "$URL" | shasum -a 256 | cut -d ' ' -f 1)

echo "--------------------------------"
echo "🆕 SHA256: $SHA"
echo "--------------------------------"

# 6. Update Formula
FORMULA_PATH="release_prep/jaavis.rb"
if [ -f "$FORMULA_PATH" ]; then
    echo "📝 Updating $FORMULA_PATH..."
    # Update URL
    sed -i '' "s|url \".*\"|url \"$URL\"|" "$FORMULA_PATH"
    # Update SHA
    sed -i '' "s|sha256 \".*\"|sha256 \"$SHA\"|" "$FORMULA_PATH"

    echo "✅ Formula updated."
    echo "👉 You should now commit and push the formula update:"
    echo "   git add $FORMULA_PATH"
    echo "   git commit -m \"Update Homebrew formula to v$VERSION\""
    echo "   git push origin main"
else
    echo "❌ Formula not found at $FORMULA_PATH"
fi

echo "🎉 Release Complete!"
