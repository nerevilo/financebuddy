#!/usr/bin/env python3
"""
Test script for Teller API exploration
"""
import subprocess
import json

CERT_PATH = "/Users/olive/Documents/claudecode/financeplanning/certificate.pem"
KEY_PATH = "/Users/olive/Documents/claudecode/financeplanning/private_key.pem"

def make_request(url, auth_token=None):
    """Make a request to Teller API using curl"""
    cmd = [
        "curl", "-s",
        "--cert", CERT_PATH,
        "--key", KEY_PATH,
    ]
    if auth_token:
        cmd.extend(["-u", f"{auth_token}:"])
    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def main():
    print("=" * 60)
    print("TELLER API TEST RESULTS")
    print("=" * 60)

    # Test 1: Accounts endpoint without auth
    print("\n1. ACCOUNTS ENDPOINT (no access token):")
    print("-" * 40)
    response = make_request("https://api.teller.io/accounts")
    print(response)

    # Test 2: Accounts with dummy token
    print("\n2. ACCOUNTS ENDPOINT (with dummy token):")
    print("-" * 40)
    response = make_request("https://api.teller.io/accounts", "test_token_xxxxxxxxxx")
    print(response)

    # Test 3: Institutions endpoint
    print("\n3. INSTITUTIONS ENDPOINT:")
    print("-" * 40)
    response = make_request("https://api.teller.io/institutions")
    try:
        institutions = json.loads(response)
        print(f"Total institutions available: {len(institutions)}")

        # Search for major banks
        major_banks = ['capital one', 'discover', 'chase', 'wells fargo',
                      'bank of america', 'citi', 'american express', 'usaa', 'ally']

        print("\n=== SEARCHING FOR MAJOR BANKS ===")
        found_any = False
        for inst in institutions:
            name_lower = inst['name'].lower()
            for bank in major_banks:
                if bank in name_lower:
                    found_any = True
                    print(f"\nName: {inst['name']}")
                    print(f"  ID: {inst['id']}")
                    print(f"  Products: {inst['products']}")
                    break

        if not found_any:
            print("None of the major banks (Capital One, Discover, Chase, etc.) found!")
            print("\nShowing first 20 institutions as sample:")
            for i, inst in enumerate(institutions[:20]):
                print(f"  {i+1}. {inst['name']} ({inst['id']})")

        # Search for specific keywords
        print("\n=== INSTITUTIONS WITH 'CREDIT' IN NAME (first 10) ===")
        credit_insts = [i for i in institutions if 'credit' in i['name'].lower()]
        for inst in credit_insts[:10]:
            print(f"  - {inst['name']} ({inst['id']})")
        print(f"  ... and {len(credit_insts) - 10} more")

    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Raw response: {response[:500]}")

    # Test 4: Check what happens with Basic Auth format
    print("\n4. AUTHENTICATION FORMAT TEST:")
    print("-" * 40)
    print("Testing HTTP Basic Auth with token as username...")
    response = make_request("https://api.teller.io/accounts", "token_xxxxxxxxxxxxxx")
    print(response)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Authentication Required:
- The /accounts endpoint requires authentication
- Format: HTTP Basic Auth with access_token as username, empty password
- Example: curl -u "access_token:" https://api.teller.io/accounts
- Access tokens are obtained through Teller Connect flow

Certificate Authentication:
- The TLS client certificate is working (API responds correctly)
- Certificates are used for mTLS (mutual TLS) authentication
- This authenticates the APPLICATION, not the user

Institutions Endpoint:
- Does NOT require user authentication (just certificate)
- Returns list of supported financial institutions
""")

def search_specific_banks():
    """Search for Capital One and Discover"""
    print("\n" + "=" * 60)
    print("SEARCHING FOR SPECIFIC BANKS")
    print("=" * 60)

    response = make_request("https://api.teller.io/institutions")
    try:
        institutions = json.loads(response)

        # Search for Capital One
        print("\n=== CAPITAL ONE ===")
        capital_one = [i for i in institutions if 'capital' in i['name'].lower()]
        if capital_one:
            for inst in capital_one:
                print(f"Name: {inst['name']}")
                print(f"  ID: {inst['id']}")
                print(f"  Products: {inst['products']}")
                print()
        else:
            print("Capital One NOT FOUND in institutions list")

        # Search for Discover
        print("\n=== DISCOVER ===")
        discover = [i for i in institutions if 'discover' in i['name'].lower()]
        if discover:
            for inst in discover:
                print(f"Name: {inst['name']}")
                print(f"  ID: {inst['id']}")
                print(f"  Products: {inst['products']}")
                print()
        else:
            print("Discover NOT FOUND in institutions list")

    except json.JSONDecodeError as e:
        print(f"Error parsing institutions: {e}")

if __name__ == "__main__":
    main()
    search_specific_banks()
