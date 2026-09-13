import os
root = r'C:\Users\USER\ilaios-clean\tools\web-factory'
for dirpath, dirnames, filenames in os.walk(root):
    if 'services' in dirpath:
        print(dirpath)