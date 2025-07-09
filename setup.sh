# !/bin/bash
sudo rm -R /usr/bin/linkfetch /usr/bin/linkfetch_src
sudo mkdir -p /usr/bin/linkfetch_src/

python3 build.py

python3 -m pip install requests flask yt_dlp --break-system-packages

sudo cp index.template /usr/bin/linkfetch_src/
sudo cp -R server.py /usr/bin/linkfetch_src/

sudo tee /usr/bin/linkfetch_src/linkfetch.sh <<EOF
# !/bin/bash
python3 /usr/bin/linkfetch_src/server.py "\$@"
EOF

sudo chmod -R 777 /usr/bin/linkfetch_src/
sudo ln -s /usr/bin/linkfetch_src/linkfetch.sh /usr/bin/linkfetch
sudo chmod 777 /usr/bin/linkfetch