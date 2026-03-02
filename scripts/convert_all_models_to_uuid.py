"""
Convert all model files to use UUID
"""
import re
from pathlib import Path

def convert_model_file(file_path):
    """Convert a single model file to use UUID"""
    content = file_path.read_text()
    
    # Check if already has UUID import
    if 'from uuid import UUID, uuid4' in content:
        print(f"✓ {file_path.name} already uses UUID")
        return False
    
    # Add UUID import
    if 'from sqlmodel import SQLModel, Field' in content:
        content = content.replace(
            'from sqlmodel import SQLModel, Field',
            'from uuid import UUID, uuid4\nfrom sqlmodel import SQLModel, Field'
        )
    
    # Replace all integer primary keys
    content = re.sub(
        r'id: Optional\[int\] = Field\(default=None, primary_key=True\)',
        'id: UUID = Field(default_factory=uuid4, primary_key=True)',
        content
    )
    
    # Replace all integer foreign keys (but not target_id, content_id which can be UUID)
    patterns = [
        (r'(\w+_id): int = Field\(foreign_key=', r'\1: UUID = Field(foreign_key='),
        (r'target_id: int', 'target_id: UUID'),
        (r'content_id: int', 'content_id: UUID'),
        (r'parent_id: Optional\[int\]', 'parent_id: Optional[UUID]'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Write back
    file_path.write_text(content)
    print(f"✓ Converted {file_path.name}")
    return True

def main():
    models_dir = Path('app/models')
    converted = 0
    
    for model_file in sorted(models_dir.glob('*.py')):
        if model_file.name == '__init__.py':
            continue
        
        if convert_model_file(model_file):
            converted += 1
    
    print(f"\n✅ Converted {converted} model files to UUID")

if __name__ == '__main__':
    main()
