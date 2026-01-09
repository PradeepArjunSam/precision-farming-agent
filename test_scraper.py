from src.tools.scraper import ScraperTool

def test_scraper():
    print("Testing Scraper Tool...")
    scraper = ScraperTool()
    
    # Test 1: Whitelisted URL (FAO)
    # Using a stable FAO page
    valid_url = "https://www.fao.org/about/en/" 
    print(f"\n[Test 1] Fetching valid URL: {valid_url}")
    result = scraper.run(valid_url)
    if result.get("status") == "success":
        print("[OK] Success")
        print(f"Content Preview: {result['content'][:100]}...")
    else:
        print(f"[FAIL] Failed: {result}")

    # Test 2: Blocked URL (Wikipedia)
    blocked_url = "https://en.wikipedia.org/wiki/Agriculture"
    print(f"\n[Test 2] Fetching blocked URL: {blocked_url}")
    result = scraper.run(blocked_url)
    if "refused" in result.get("message", "").lower():
        print(f"[OK] Correctly Refused: {result['message']}")
    else:
        print(f"[FAIL] Unexpected result: {result}")

if __name__ == "__main__":
    test_scraper()
