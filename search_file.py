import os
target = 'browser_egress_docker.py'
for root, dirs, files in os.walk(r'C:\Users\USER\ilaios-clean'):
    for f in files:
        if target in f:
            print(os.path.join(root, f))
print("Done searching")