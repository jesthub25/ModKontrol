set -e
mkdir -p out/server && cd out/server
B=$(curl -s https://api.papermc.io/v2/projects/paper/versions/1.21.1/builds | jq -r '.builds | map(select(.channel=="default")) | last | .build')
curl -s -o paper.jar "https://api.papermc.io/v2/projects/paper/versions/1.21.1/builds/$B/downloads/paper-1.21.1-$B.jar"
echo "build $B"
java -Dpaperclip.patchonly=true -jar paper.jar
ls -la . versions cache || true
du -sh libraries versions cache
