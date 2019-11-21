mkdir .temp
mkdir .temp/server
mkdir .temp/client

pandoc report.md -s -o report.pdf

cp report.pdf .temp
cp server/server.py .temp/server
cp server/UserManager.py .temp/server
cp server/credentials.txt .temp/server
cp client/client.py .temp/client

tar -cvf assign.tar .temp

rm -rf .temp

scp assign.tar cse:~/3331
ssh cse "cd 3331; give cs3331 assign assign.tar"
