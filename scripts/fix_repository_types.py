#!/usr/bin/env python3
"""
Fix all repository method parameters from int to UUID
"""

import re
from pathlib import Path


def fix_file(filepath):
    """Fix int type hints to UUID in a single file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Add UUID import if not present
    if 'from uuid import UUID' not in content and 'from uuid import' not in content:
        # Find the imports section and add UUID
        if 'from typing import' in content:
            content = content.replace(
                'from typing import',
                'from uuid import UUID\nfrom typing import'
            )
        elif 'from sqlmodel import' in content:
            content = content.replace(
                'from sqlmodel import',
                'from uuid import UUID\nfrom sqlmodel import'
            )
    
    # Fix method parameters - be careful to only match function parameters
    # Pattern: parameter_name: int) or parameter_name: int,
    content = re.sub(r'\b(user_id|model_id|collection_id|bounty_id|community_id|post_id|ticket_id|transaction_id|admin_id|creator_id|buyer_id|seller_id|artist_id|applicant_id|poster_id|author_id|sender_id|reporter_id|follower_id|following_id|parent_id): int([,\)])', r'\1: UUID\2', content)
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False


def main():
    """Fix all repository files"""
    repo_dir = Path('app/repositories')
    
    print("Fixing repository method parameters to use UUID...")
    print("=" * 60)
    
    fixed_count = 0
    for filepath in repo_dir.glob('*.py'):
        if filepath.name == '__init__.py':
            continue
        if fix_file(filepath):
            print(f"✅ Fixed: {filepath}")
            fixed_count += 1
        else:
            print(f"⏭️  Skipped: {filepath} (no changes needed)")
    
    print("=" * 60)
    print(f"\n✅ Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
