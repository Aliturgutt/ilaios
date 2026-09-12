import os

# Create web factory acceptance inventory
wf_dir = 'tools/web-factory/skills'
wf_skills = sorted([d for d in os.listdir(wf_dir) if os.path.isdir(os.path.join(wf_dir, d))])

print('=== ACCEPTANCE INVENTORY: Web Factory Skills ===')
print(f'Total web-factory skills: {len(wf_skills)}')
print()

# List all skills with evidence paths
for s in wf_skills:
    skill_dir = os.path.join(wf_dir, s)
    contract = os.path.join(skill_dir, 'CONTRACT.md')
    provenance = os.path.join(skill_dir, 'PROVENANCE.md')
    readme = os.path.join(skill_dir, 'README.md')
    print(f'Skill: {s}')
    print(f'  Path: {skill_dir}')
    print(f'  CONTRACT.md exists: {os.path.exists(contract)}')
    print(f'  PROVENANCE.md exists: {os.path.exists(provenance)}')
    print(f'  README.md exists: {os.path.exists(readme)}')
    print()