#!/bin/bash
# Download the Google Fonts (OFL) used by the components into remotion/public/fonts and fonts/.
cd "$(dirname "$0")" && mkdir -p remotion/public/fonts fonts
get() { curl -s "https://fonts.googleapis.com/css2?family=$1" | grep -oE "https://fonts.gstatic.com/[^)]+\.ttf" | head -1 | xargs -I{} curl -s -o "remotion/public/fonts/$2" {}; cp "remotion/public/fonts/$2" "fonts/$2"; }
get "Libre+Baskerville:wght@400" LibreBaskerville-Regular.ttf
get "Libre+Baskerville:wght@700" LibreBaskerville-Bold.ttf
get "Anton" Anton-Regular.ttf
get "Montserrat:wght@900" Montserrat-Black.ttf
get "Montserrat:wght@800" Montserrat-ExtraBold.ttf
get "Cinzel:wght@600" Cinzel-SemiBold.ttf
get "Special+Elite" SpecialElite-Regular.ttf
ls remotion/public/fonts
