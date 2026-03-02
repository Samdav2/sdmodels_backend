#!/usr/bin/env python3
"""
Quick diagnostic: Check which user you're currently logged in as
and what sender_type their messages should have
"""
import sys

print("="*80)
print("QUICK DIAGNOSTIC: Who are you logged in as?")
print("="*80)

print("\n📋 Current Users in Database:")
print("-"*80)
print("Email                          User Type    Expected sender_type")
print("-"*80)
print("adoxop1@gmail.com              admin        admin (LEFT side)")
print("test_client_bounty@example.com buyer        user  (RIGHT side)")
print("bloggers694@gmail.com          creator      user  (RIGHT side)")
print("-"*80)

print("\n💡 HOW TO CHECK:")
print("1. Open browser DevTools (F12)")
print("2. Go to Application/Storage → Local Storage")
print("3. Look for 'token' or 'user' data")
print("4. OR check Network tab when loading the page")
print("5. Look for /api/v1/users/me request")
print("6. Check the 'user_type' field in response")

print("\n🔍 EXPECTED BEHAVIOR:")
print("- If logged in as 'admin' → messages appear on LEFT (admin side)")
print("- If logged in as 'buyer' or 'creator' → messages appear on RIGHT (user side)")

print("\n⚠️  COMMON ISSUE:")
print("If you're logged in as adoxop1@gmail.com (admin), your messages will")
print("ALWAYS appear on the LEFT side. This is CORRECT behavior for admins.")
print("\nTo test user messages, login as:")
print("  - bloggers694@gmail.com (creator)")
print("  - test_client_bounty@example.com (buyer)")

print("\n" + "="*80)
print("QUICK TEST:")
print("="*80)
print("Run this in your browser console while logged in:")
print()
print("fetch('/api/v1/users/me', {")
print("  headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }")
print("})")
print(".then(r => r.json())")
print(".then(data => {")
print("  console.log('Logged in as:', data.email);")
print("  console.log('User type:', data.user_type);")
print("  console.log('Messages will appear as:', data.user_type === 'admin' ? 'admin (LEFT)' : 'user (RIGHT)');")
print("});")

print("\n" + "="*80)
