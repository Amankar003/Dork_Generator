#!/usr/bin/env python
"""
Cleanup India Recommendations Script.

Run this script to immediately delete any old recommendations in the SQLite database
that target Indian locations, trends, or contain site:.in dorks.
"""

from database import delete_india_recommendations

def main():
    print("=" * 60)
    print("RUNNING DB CLEANUP: REMOVING INDIA RECOMMENDATIONS")
    print("=" * 60)
    
    try:
        deleted_count = delete_india_recommendations()
        print(f"Success! Deleted {deleted_count} Indian market recommendations from the database.")
    except Exception as e:
        print(f"Error during database cleanup: {e}")
        
    print("=" * 60)

if __name__ == "__main__":
    main()
