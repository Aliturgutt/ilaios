import os
runtime_dir = r'C:\Users\USER\ilaios-clean\tools\web-factory\browser-skills\runtime'
print("Directory contents:")
try:
    files = os.listdir(runtime_dir)
    for f in sorted(files):
        print(f"  {f}")
except Exception as e:
    print(f"Error: {e}")