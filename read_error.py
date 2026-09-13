path = r'C:\Users\USER\ilaios-clean\tools\web-factory\services\runtime\browser_egress_docker.py'
with open(path) as f:
    lines = f.readlines()
    for i in range(284, 291):  # 0-indexed, so 285 is index 284
        print(f'{i+1}: {lines[i].rstrip()}')