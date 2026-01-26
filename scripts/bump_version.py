import sys
import re
from pathlib import Path
from datetime import datetime

if len(sys.argv) != 2 or sys.argv[1] not in ['patch', 'minor', 'major']:
    print("Usage: python bump_version.py <patch|minor|major>")
    sys.exit(1)

bump_type = sys.argv[1]

# Read pyproject.toml
with open('pyproject.toml', 'r') as f:
    content = f.read()

# Find version
version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
if not version_match:
    print("Could not find version in pyproject.toml")
    sys.exit(1)

version = version_match.group(1)
major, minor, patch = map(int, version.split('.'))

if bump_type == 'patch':
    patch += 1
elif bump_type == 'minor':
    minor += 1
    patch = 0
elif bump_type == 'major':
    major += 1
    minor = 0
    patch = 0

new_version = f"{major}.{minor}.{patch}"

# Replace version in content
new_content = re.sub(r'(version\s*=\s*)"[^"]*"', rf'\1"{new_version}"', content)

# Write back
with open('pyproject.toml', 'w') as f:
    f.write(new_content)

# Update __init__.py
init_file = Path('src/projektor/__init__.py')
lines = init_file.read_text().split('\n')
for i, line in enumerate(lines):
    if line.startswith('__version__ = '):
        lines[i] = f'__version__ = "{new_version}"'
        break
init_file.write_text('\n'.join(lines))

# Update CHANGELOG.md
changelog_file = Path('CHANGELOG.md')
changelog_content = changelog_file.read_text()
date_str = datetime.now().strftime("%Y-%m-%d")
new_changelog = changelog_content.replace("## [Unreleased]", f"## [{new_version}] - {date_str}", 1)
new_changelog += "\n## [Unreleased]\n"
changelog_file.write_text(new_changelog)

print(f"Version bumped to {new_version}")
