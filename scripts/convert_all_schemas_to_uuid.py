"""
Convert all schema files to use UUID
"""
import re
from pathlib import Path

def convert_schema_file(file_path):
    """Convert a single schema file to use UUID"""
    content = file_path.read_text()
    
    # Check if already has UUID import
    if 'from uuid import UUID' in content:
        print(f"✓ {file_path.name} already uses UUID")
        return False
    
    # Add UUID import after other imports
    if 'from pydantic import BaseModel' in content:
        content = content.replace(
            'from pydantic import BaseModel',
            'from uuid import UUID\nfrom pydantic import BaseModel'
        )
    elif 'from typing import' in content:
        # Add after first import
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('from typing import'):
                lines.insert(i+1, 'from uuid import UUID')
                break
        content = '\n'.join(lines)
    
    # Replace all integer IDs with UUID
    patterns = [
        (r'id: int', 'id: UUID'),
        (r'(\w+_id): int', r'\1: UUID'),
        (r'Optional\[int\] = None', 'Optional[UUID] = None'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Write back
    file_path.write_text(content)
    print(f"✓ Converted {file_path.name}")
    return True

def main():
    schemas_dir = Path('app/schemas')
    converted = 0
    
    for schema_file in sorted(schemas_dir.glob('*.py')):
        if schema_file.name == '__init__.py':
            continue
        
        if convert_schema_file(schema_file):
            converted += 1
    
    print(f"\n✅ Converted {converted} schema files to UUID")

if __name__ == '__main__':
    main()
