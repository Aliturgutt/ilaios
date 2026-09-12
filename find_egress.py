import os
runtime_dir = r'C:\Users\USER\ilaios-clean\tools\web-factory\browser-skills\runtime'
for f in os.listdir(runtime_dir):
    if 'egress' in f.lower():
        print(f)
        with open(os.path.join(runtime_dir, f)) as fh:
            lines = fh.readlines()
            for i, line in enumerate(lines[280:290], start=281):
                print(f'{i}: {line.rstrip()}')