#!/usr/bin/env python3

import sqlite3
import requests
import json

print("=== Testing Feedback System ===")

# Test database
print("\n1. Testing database:")
try:
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT username, feedback, created_at FROM feedback ORDER BY created_at DESC')
    rows = c.fetchall()
    print(f"Found {len(rows)} feedback entries:")
    for row in rows:
        print(f"  - {row[0]}: {row[1]} ({row[2]})")
    conn.close()
except Exception as e:
    print(f"Database error: {e}")

# Test API endpoint
print("\n2. Testing API endpoint:")
try:
    response = requests.get('http://127.0.0.1:5000/get-feedback', timeout=5)
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"API returned {len(data)} items:")
        for item in data:
            print(f"  - {item['username']}: {item['feedback']}")
    else:
        print(f"API error: {response.text}")
except Exception as e:
    print(f"API error: {e}")

print("\n=== Test Complete ===")
