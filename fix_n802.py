with open('C:\\Users\\USER\\ilaios-clean\\src\\code_intelligence\\repository_analyzer.py') as f:
    lines = f.readlines()
    for i in range(231, 263):
        print(f'{i+1}: {lines[i].rstrip()}')