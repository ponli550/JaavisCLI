#!/bin/bash
set -e

# Jaavis Release Automation
# Usage: ./scripts/publish.sh

echo "🚀 Jaavis Release Protocol"
echo "--------------------------------"

# 1. Extract Current Version
CURRENT_VERSION=$(grep 'VERSION =' jaavis_core.py | cut -d '"' -f 2)
echo "📦 Current Version: $CURRENT_VERSION"

# 2. Select Bump Type
echo "Select Release Type:"
echo "  1) Patch (x.x.+1) - Bug fixes"
echo "  2) Minor (x.+1.0) - New features"
echo "  3) Major (+1.0.0) - Breaking changes"
read -p "Choice (1-3): " -n 1 -r
echo

IFS='.' read -r -a parts <<< "$CURRENT_VERSION"
MAJOR=${parts[0]}
MINOR=${parts[1]}
PATCH=${parts[2]}

if [[ $REPLY == "1" ]]; then
    NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
elif [[ $REPLY == "2" ]]; then
    NEW_VERSION="$MAJOR.$((MINOR + 1)).0"
elif [[ $REPLY == "3" ]]; then
    NEW_VERSION="$((MAJOR + 1)).0.0"
else
    echo "Invalid choice. Aborting."
    exit 1
fi

echo "🎯 Target Version: $NEW_VERSION"

# Safety Check
# (Simple string comparison sufficient for now as we just constructed it to be larger)
read -p "❓ Proceed with release v$NEW_VERSION? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# 3. Update jaavis_core.py
# sed difference for Mac/Linux
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/VERSION = \"$CURRENT_VERSION\"/VERSION = \"$NEW_VERSION\"/" jaavis_core.py
else
    sed -i "s/VERSION = \"$CURRENT_VERSION\"/VERSION = \"$NEW_VERSION\"/" jaavis_core.py
fi
echo "✅ Updated jaavis_core.py to $NEW_VERSION"

# 4. Git Commit & Tag
if [[ -n $(git status -s) ]]; then
    git add jaavis_core.py
    git commit -m "Release v$NEW_VERSION"
fi

echo "🏷️  Tagging v$NEW_VERSION..."
git tag "v$NEW_VERSION"

echo "⬆️  Pushing to origin..."
git push origin main
git push origin "v$NEW_VERSION"
echo "✅ Code released to GitHub."

# 5. Homebrew Update Calculation
echo "🍺 Calculating SHA256 for Homebrew..."
URL="https://github.com/ponli550/JaavisCLI/archive/refs/tags/v$NEW_VERSION.tar.gz"
echo "   Waiting for GitHub to generate tarball..."
sleep 5

# Download and calc hash
SHA=$(curl -sL "$URL" | shasum -a 256 | cut -d ' ' -f 1)
echo "   SHA256: $SHA"

# 6. Automate Homebrew Tap Update
TAP_REPO="https://github.com/ponli550/homebrew-jaavis.git"
TEMP_DIR="/tmp/jaavis-homebrew-release-$(date +%s)"

echo "🍺 Updating Homebrew Tap ($TAP_REPO)..."
git clone "$TAP_REPO" "$TEMP_DIR"

FORMULA_PATH="$TEMP_DIR/Formula/jaavis.rb"
# If formula is in root, handle that
if [ ! -f "$FORMULA_PATH" ]; then
    FORMULA_PATH="$TEMP_DIR/jaavis.rb"
fi

if [ -f "$FORMULA_PATH" ]; then
    echo "📝 Updating $FORMULA_PATH..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|url \".*\"|url \"$URL\"|" "$FORMULA_PATH"
        sed -i '' "s|sha256 \".*\"|sha256 \"$SHA\"|" "$FORMULA_PATH"
    else
        sed -i "s|url \".*\"|url \"$URL\"|" "$FORMULA_PATH"
        sed -i "s|sha256 \".*\"|sha256 \"$SHA\"|" "$FORMULA_PATH"
    fi

    # Commit and Push
    cd "$TEMP_DIR"
    git config user.email "jaavis-bot@ponli550.com"
    git config user.name "Jaavis Release Bot"
    git add .
    git commit -m "Update jaavis to v$NEW_VERSION"
    git push origin main
    cd - > /dev/null

    echo "✅ Homebrew Tap Updated!"
else
    echo "❌ Could not find jaavis.rb in cloned tap."
fi

# Cleanup
rm -rf "$TEMP_DIR"
echo "🎉 Release Complete!"
