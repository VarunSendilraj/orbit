#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting Orbit build process..."

# Create dist directory
mkdir -p ../dist/{agent,app,helper}

# 1) Build agent
echo "📦 Building Python agent..."
cd ../agent/oribit_agent
uv run pyinstaller --onefile -n orbit-agent src/oribit_agent/server.py
mkdir -p ../../dist/agent && mv dist/orbit-agent ../../dist/agent/
echo "✅ Agent build complete"

# 2) Build app (Tauri)
echo "🌐 Building Tauri app..."
cd ../../app/Orbit
pnpm install
pnpm run tauri build
mkdir -p ../../dist/app && cp -R src-tauri/target/release/bundle/macos/*.app ../../dist/app/ || true
echo "✅ App build complete"

# 3) Build helper via Xcode
echo "🛠️  Building Swift helper..."
cd ../../helper/OrbitHelper
xcodebuild -scheme OrbitHelper -configuration Release -derivedDataPath build
mkdir -p ../../dist/helper && cp build/Build/Products/Release/OrbitHelper ../../dist/helper/
echo "✅ Helper build complete"

echo "🎉 All builds complete! Check dist/ directory for artifacts"
ls -la ../dist/*/