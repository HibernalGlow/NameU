
import pytest
import os
import sys

# Ensure src is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from nameu.core import config

def test_blacklist_functionality():
    """Test path blacklist and keyword blacklist functionality"""
    
    # Mock configuration
    original_blacklist = config.path_blacklist
    original_keywords = config.path_blacklist_keywords
    
    try:
        # Define test paths
        base_dir = os.getcwd()
        blocked_path = os.path.join(base_dir, "blocked_folder")
        sub_blocked_path = os.path.join(blocked_path, "subfolder")
        safe_path = os.path.join(base_dir, "safe_folder")
        keyword_blocked_path = os.path.join(base_dir, "some_[weibo]_content")
        
        # 1. Test Path Blacklist (Direct & Recursive)
        config.path_blacklist = [blocked_path]
        config.path_blacklist_keywords = []
        
        print("\nTesting Path Blacklist:")
        print(f"Blocked path: {blocked_path}")
        print(f"Config blacklist: {config.path_blacklist}")
        
        is_blocked = config.is_path_blacklisted(blocked_path)
        print(f"Result for blocked_path: {is_blocked}")
        
        assert is_blocked == True, f"Direct blacklist match failed. Path: {blocked_path} in {config.path_blacklist}"
        print("✓ Direct match passed")
        
        is_sub_blocked = config.is_path_blacklisted(sub_blocked_path)
        print(f"Result for sub_blocked_path: {is_sub_blocked}")
        assert is_sub_blocked == True, "Recursive blacklist match failed"
        print("✓ Recursive match passed")
        
        is_safe_blocked = config.is_path_blacklisted(safe_path)
        print(f"Result for safe_path: {is_safe_blocked}")
        assert is_safe_blocked == False, "Safe path falsely blacklisted"
        print("✓ Safe path passed")
        
        # 2. Test Keyword Blacklist
        config.path_blacklist = []
        config.path_blacklist_keywords = ["[weibo]", "[TEST]"]
        
        print("\nTesting Keyword Blacklist:")
        print(f"Keywords: {config.path_blacklist_keywords}")
        
        is_keyword_blocked = config.is_path_blacklisted(keyword_blocked_path)
        print(f"Result for keyword_blocked_path ({keyword_blocked_path}): {is_keyword_blocked}")
        assert is_keyword_blocked == True, "Keyword 'weibo' match failed"
        print("✓ Keyword match passed")
        
        # Case insensitivity check
        upper_keyword_path = os.path.join(base_dir, "SOME_WEIBO_CONTENT")
        is_upper_blocked = config.is_path_blacklisted(upper_keyword_path)
        print(f"Result for upper_keyword_path ({upper_keyword_path}): {is_upper_blocked}")
        assert is_upper_blocked == True, "Keyword match should be case-insensitive"
        print("✓ Case insensitive match passed")
        
        is_safe_blocked_kw = config.is_path_blacklisted(safe_path)
        print(f"Result for safe_path (keyword): {is_safe_blocked_kw}")
        assert is_safe_blocked_kw == False, "Safe path falsely blocked by keywords"
        print("✓ Safe path passed")
        
    finally:
        # Restore configuration
        config.path_blacklist = original_blacklist
        config.path_blacklist_keywords = original_keywords

if __name__ == "__main__":
    try:
        test_blacklist_functionality()
        print("\nAll blacklist tests passed!")
    except AssertionError as e:
        print(f"\nTest Failed: {e}")
    except Exception as e:
        print(f"\nError: {e}")
