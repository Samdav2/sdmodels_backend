#!/usr/bin/env python3
"""
Fix all endpoint path parameters from int to UUID
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
        elif 'from fastapi import' in content:
            content = content.replace(
                'from fastapi import',
                'from uuid import UUID\nfrom fastapi import'
            )
    
    # Fix path parameters: model_id: int -> model_id: UUID
    content = re.sub(r'\bmodel_id: int\b', 'model_id: UUID', content)
    
    # Fix path parameters: user_id: int -> user_id: UUID
    content = re.sub(r'\buser_id: int\b', 'user_id: UUID', content)
    
    # Fix path parameters: collection_id: int -> collection_id: UUID
    content = re.sub(r'\bcollection_id: int\b', 'collection_id: UUID', content)
    
    # Fix path parameters: bounty_id: int -> bounty_id: UUID
    content = re.sub(r'\bbounty_id: int\b', 'bounty_id: UUID', content)
    
    # Fix path parameters: community_id: int -> community_id: UUID
    content = re.sub(r'\bcommunity_id: int\b', 'community_id: UUID', content)
    
    # Fix path parameters: post_id: int -> post_id: UUID
    content = re.sub(r'\bpost_id: int\b', 'post_id: UUID', content)
    
    # Fix path parameters: ticket_id: int -> ticket_id: UUID
    content = re.sub(r'\bticket_id: int\b', 'ticket_id: UUID', content)
    
    # Fix path parameters: transaction_id: int -> transaction_id: UUID
    content = re.sub(r'\btransaction_id: int\b', 'transaction_id: UUID', content)
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False


def main():
    """Fix all endpoint files"""
    endpoint_dir = Path('app/api/v1/endpoints')
    
    print("Fixing endpoint path parameters to use UUID...")
    print("=" * 60)
    
    fixed_count = 0
    for filepath in endpoint_dir.glob('*.py'):
        if fix_file(filepath):
            print(f"✅ Fixed: {filepath}")
            fixed_count += 1
        else:
            print(f"⏭️  Skipped: {filepath} (no changes needed)")
    
    print("=" * 60)
    print(f"\n✅ Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
