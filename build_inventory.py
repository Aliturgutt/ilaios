import os

# Create acceptance inventory mapping
sf_dir = 'tools/software-factory/skills'
sf_skills = sorted([d for d in os.listdir(sf_dir) if os.path.isdir(os.path.join(sf_dir, d)) and d != 'sf-windows-desktop'])

print('=== ACCEPTANCE INVENTORY: Software Factory 24 Skills ===')
print(f'Total in-scope skills: {len(sf_skills)}')
print()

# List all skills with evidence paths
for s in sf_skills:
    skill_dir = os.path.join(sf_dir, s)
    contract = os.path.join(skill_dir, 'CONTRACT.md')
    provenance = os.path.join(skill_dir, 'PROVENANCE.md')
    print(f'Skill: {s}')
    print(f'  Path: {skill_dir}')
    print(f'  CONTRACT.md exists: {os.path.exists(contract)}')
    print(f'  PROVENANCE.md exists: {os.path.exists(provenance)}')
    print()