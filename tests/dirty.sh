#!/bin/sh

git init
git config user.email "you@example.com"
git config user.name "Your Name"
touch README.rst
git add README.rst
git commit -m "first commit"
git tag 1.2.3.rc1
cat <<< 'EOF' >> README.rst
Hello world!
EOF
git commit -am "second commit"
cat <<< 'EOF' >> README.rst
Holà mundo!
EOF
