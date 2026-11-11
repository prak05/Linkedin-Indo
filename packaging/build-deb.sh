#!/bin/sh
# Build a .deb of LinkedIn Indo (CLI + local web UI).
#
# Run:  sh packaging/build-deb.sh        -> dist/linkedin-indo_<version>_<arch>.deb
#
# The app installs to /usr/lib/linkedin-indo with its Python dependencies
# bundled in vendor/, so it does not depend on packages in ~/.local.
# Drafts and style samples live in ~/.local/share/linkedin-indo/.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pyproject.toml")
# Bundled wheels (pydantic-core, jiter) are compiled, so the package is arch-specific.
ARCH=$(dpkg --print-architecture)
PKG=linkedin-indo
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

APP="$STAGE/usr/lib/$PKG"
mkdir -p "$APP" "$STAGE/usr/bin" "$STAGE/usr/share/doc/$PKG" "$STAGE/DEBIAN" "$ROOT/dist"

cp "$ROOT/app.py" "$ROOT/local_server.py" "$ROOT/desktop.py" "$ROOT/aws_connect.py" "$ROOT/index.html" "$ROOT/config.js" "$ROOT/verify-motion.js" "$APP/"
mkdir -p "$APP/src" "$APP/infrastructure" "$APP/vendor" "$APP/packaging"
# Front-end runtime, bundled so the UI works offline.
cp "$ROOT/vendor/tailwindcss-browser-4.3.3.js" "$ROOT/vendor/tailwindcss-LICENSE" "$APP/vendor/"
cp "$ROOT/packaging/linkedin-indo.svg" "$APP/packaging/"
cp -r "$ROOT/src/indo_core" "$ROOT/src/handlers" "$ROOT/src/requirements-lambda.txt" "$APP/src/"
# Terraform code for linkedin-indo-aws (state stays in ~/.local/share/linkedin-indo/aws).
cp "$ROOT"/infrastructure/*.tf "$ROOT/infrastructure/.terraform.lock.hcl" "$APP/infrastructure/"
cp "$ROOT/samples/README.md" "$APP/samples-README.md"
cp -r "$ROOT/samples" "$ROOT/persona" "$ROOT/projects" "$ROOT/resumes" "$APP/"
find "$APP" -name __pycache__ -prune -exec rm -rf {} +

python3.13 -m pip install --quiet --no-compile --disable-pip-version-check \
    -r "$ROOT/requirements.txt" -t "$APP/vendor"
rm -rf "$APP/vendor/bin"

# Shared launcher: data dirs, bundled deps, and the right interpreter.
cat > "$APP/launch" <<'EOF'
#!/bin/sh
set -eu
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/linkedin-indo"
export INDO_POSTS_DIR="${INDO_POSTS_DIR:-$DATA/posts}"
export INDO_SAMPLES_DIR="${INDO_SAMPLES_DIR:-$DATA/samples}"
export INDO_CLOUD_CONFIG="${INDO_CLOUD_CONFIG:-$DATA/aws/config.cloud.js}"
export INDO_PERSONA_DIR="${INDO_PERSONA_DIR:-$DATA/persona}"
export INDO_VECTORDB_PATH="${INDO_VECTORDB_PATH:-$DATA/vectordb/knowledge.db}"
mkdir -p "$INDO_POSTS_DIR" "$INDO_SAMPLES_DIR" "$INDO_PERSONA_DIR" "$DATA/vectordb"
if [ -d /usr/lib/linkedin-indo/persona ] && [ ! -f "$INDO_PERSONA_DIR/persona.json" ]; then
    cp -r /usr/lib/linkedin-indo/persona/* "$INDO_PERSONA_DIR/" 2>/dev/null || true
fi
if [ -d /usr/lib/linkedin-indo/samples ]; then
    cp -n /usr/lib/linkedin-indo/samples/* "$INDO_SAMPLES_DIR/" 2>/dev/null || true
fi
if [ -x /usr/bin/python3.13 ]; then PY=/usr/bin/python3.13
elif command -v python3.13 >/dev/null 2>&1; then PY=$(command -v python3.13)
else echo "linkedin-indo: python3.13 not found" >&2; exit 1; fi
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$APP_DIR/vendor:$APP_DIR/src:${PYTHONPATH:-}"
export PYTHONDONTWRITEBYTECODE=1
echo "Drafts: $INDO_POSTS_DIR   Style samples: $INDO_SAMPLES_DIR" >&2
script="$1"; shift
exec "$PY" -s "$APP_DIR/$script" "$@"
EOF
chmod 755 "$APP/launch"

printf '#!/bin/sh\nexec /usr/lib/linkedin-indo/launch app.py "$@"\n' > "$STAGE/usr/bin/linkedin-indo"
printf '#!/bin/sh\nexec /usr/lib/linkedin-indo/launch local_server.py "$@"\n' > "$STAGE/usr/bin/linkedin-indo-server"
printf '#!/bin/sh\nexec /usr/lib/linkedin-indo/launch aws_connect.py "$@"\n' > "$STAGE/usr/bin/linkedin-indo-aws"
printf '#!/bin/sh\nexec /usr/lib/linkedin-indo/launch desktop.py "$@"\n' > "$STAGE/usr/bin/linkedin-indo-desktop"
chmod 755 "$STAGE"/usr/bin/linkedin-indo*

# Desktop app: apps-menu entry and icon.
mkdir -p "$STAGE/usr/share/applications" "$STAGE/usr/share/icons/hicolor/scalable/apps"
cp "$ROOT/packaging/linkedin-indo.desktop" "$STAGE/usr/share/applications/"
cp "$ROOT/packaging/linkedin-indo.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/"

cp "$ROOT/README.md" "$ROOT/PRD.md" "$STAGE/usr/share/doc/$PKG/"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Architecture: $ARCH
Maintainer: Prak <prak05@localhost>
Depends: python3.13
Recommends: chromium | google-chrome-stable | brave-browser, poppler-utils, tesseract-ocr
Suggests: awscli, terraform
Section: utils
Priority: optional
Installed-Size: $(du -sk "$STAGE/usr" | cut -f1)
Description: Draft LinkedIn posts and comments in your voice
 Desktop app (LinkedIn Indo in the apps menu, or linkedin-indo-desktop),
 guided CLI (linkedin-indo) and local web UI (linkedin-indo-server) that
 turn event facts into a LinkedIn draft. The desktop window needs a
 Chromium-based browser (Chromium, Chrome or Brave).
 Two engines: an offline local model (no AI service), or an LLM through an
 API: Claude via Anthropic or Amazon Bedrock, OpenAI, Gemini, Groq,
 OpenRouter or Ollama. Nothing is posted automatically.
 Settings stores API keys and AWS credentials for apps-menu launches. The
 Agent is a chat assistant on Claude that searches the web, reads pages and
 public LinkedIn profiles, and (with your approval) writes files and runs
 commands in a workspace folder. Scan reads your public LinkedIn profile
 into your persona.
 poppler-utils and tesseract-ocr let the local engine read PDFs and images.
 linkedin-indo-aws signs in to your AWS account and deploys the cloud
 backend (needs AWS CLI v2.32+ and Terraform).
EOF

find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type f -exec chmod go-w {} +

OUT="$ROOT/dist/${PKG}_${VERSION}_${ARCH}.deb"
fakeroot dpkg-deb --build -Zxz "$STAGE" "$OUT" >/dev/null
echo "$OUT"
