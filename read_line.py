with open(r'C:\Users\USER\ilaios-clean\services\runtime\browser_egress_docker.py') as f:
    lines = f.readlines()
    # Show context around line 285
    for i in range(275, 295):
        print(f"{i+1}: {lines[i].rstrip()}")