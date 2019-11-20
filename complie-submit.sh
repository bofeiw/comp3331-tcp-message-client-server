tar -cvf assign.tar client server report.md
scp assign.tar cse:~/3331
ssh cse "cd 3331; give cs3331 assign assign.tar"
