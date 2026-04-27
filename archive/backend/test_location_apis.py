"""
Test Different Approaches to Get Store Locations

Comparing:
1. Google Places API (paid)
2. OpenStreetMap/Nominatim (free)
3. LLM-based extraction (GPT-3.5/4)
"""
import os
import httpx
import asyncio


async def test_google_places(query: str, api_key: str = None):
    """
    Google Places API - Find businesses by name

    Cost: $0.017 per query (Text Search)
    Accuracy: Very High
    """
    if not api_key:
        print("⚠️  Google Places: Need API key (GOOGLE_PLACES_API_KEY)")
        print("   Get one at: https://console.cloud.google.com/")
        return None

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "key": api_key
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()

            if data.get("results"):
                place = data["results"][0]
                return {
                    "name": place.get("name"),
                    "address": place.get("formatted_address"),
                    "location": place.get("geometry", {}).get("location"),
                    "rating": place.get("rating"),
                    "source": "google_places"
                }
    except Exception as e:
        print(f"Google Places error: {e}")

    return None


async def test_nominatim(query: str):
    """
    OpenStreetMap Nominatim - FREE geocoding

    Cost: FREE
    Accuracy: Medium (not all stores have detailed data)
    Rate Limit: 1 request/second
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "FinTrack/1.0"  # Required by Nominatim
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            data = response.json()

            if data:
                place = data[0]
                return {
                    "name": place.get("display_name"),
                    "latitude": float(place.get("lat")),
                    "longitude": float(place.get("lon")),
                    "source": "openstreetmap"
                }
    except Exception as e:
        print(f"Nominatim error: {e}")

    return None


async def test_llm_extraction(description: str, openai_api_key: str = None):
    """
    LLM-based extraction using GPT-3.5

    Cost: ~$0.002 per query (GPT-3.5-turbo)
    Accuracy: Unknown (depends on training data)
    """
    if not openai_api_key:
        print("⚠️  OpenAI: Need API key (OPENAI_API_KEY)")
        print("   Get one at: https://platform.openai.com/")
        return None

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""Given this transaction description, extract what you know about the business location:

Transaction: "{description}"

If you know the specific store location, provide:
- Store address
- City, State
- GPS coordinates (if known)

If you don't know the specific store, say "I don't have information about this specific store location."

Respond in JSON format:
{{
    "merchant": "...",
    "address": "...",
    "city": "...",
    "state": "...",
    "known": true/false
}}"""

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that extracts business location information."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            data = response.json()

            if "choices" in data:
                content = data["choices"][0]["message"]["content"]
                return {
                    "response": content,
                    "source": "llm_gpt35",
                    "cost": 0.002  # Approximate
                }
    except Exception as e:
        print(f"OpenAI error: {e}")

    return None


async def test_all_approaches():
    """Test all approaches on sample transaction"""

    # Sample transaction from your database
    description = "Debit Card Purchase - HARDEE'S 594"
    merchant = "Hardee's"
    store_number = "594"

    print("🧪 TESTING LOCATION EXTRACTION METHODS")
    print("=" * 80)
    print(f"\nTransaction: {description}")
    print(f"Extracted: {merchant} store #{store_number}")
    print("\n" + "=" * 80)

    # Get API keys from environment
    google_key = os.getenv("GOOGLE_PLACES_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # Test 1: Google Places
    print("\n1. 🌐 Google Places API (Paid - $0.017/query)")
    print("-" * 80)
    result = await test_google_places(f"{merchant} {store_number}", google_key)
    if result:
        print(f"✅ Found: {result['name']}")
        print(f"   Address: {result['address']}")
        print(f"   Location: {result['location']}")
        print(f"   Rating: {result.get('rating', 'N/A')}")
    else:
        print("   (Need API key to test - but would likely work)")

    # Test 2: OpenStreetMap
    print("\n2. 🗺️  OpenStreetMap/Nominatim (FREE)")
    print("-" * 80)
    result = await test_nominatim(f"{merchant} {store_number}")
    if result:
        print(f"✅ Found: {result['name']}")
        print(f"   Coordinates: {result['latitude']}, {result['longitude']}")
    else:
        print("❌ Not found (limited coverage)")

    # Give it a second (rate limit)
    await asyncio.sleep(1.5)

    # Test 3: Try with city hint
    print("\n3. 🗺️  OpenStreetMap with City Hint")
    print("-" * 80)
    # If transaction had city: "HARDEE'S 594 FRANKLIN TN"
    result = await test_nominatim(f"{merchant} Franklin TN")
    if result:
        print(f"✅ Found: {result['name']}")
        print(f"   Coordinates: {result['latitude']}, {result['longitude']}")
    else:
        print("❌ Not found")

    await asyncio.sleep(1.5)

    # Test 4: LLM
    print("\n4. 🤖 LLM (GPT-3.5) - $0.002/query")
    print("-" * 80)
    result = await test_llm_extraction(description, openai_key)
    if result:
        print(f"Response: {result['response']}")
        print(f"Cost: ${result['cost']}")
    else:
        print("   (Need OpenAI API key to test)")

    print("\n" + "=" * 80)
    print("\n📊 COMPARISON:")
    print("-" * 80)
    print("Method                  | Cost      | Accuracy | Coverage")
    print("-" * 80)
    print("Google Places           | $0.017    | ⭐⭐⭐⭐⭐   | ⭐⭐⭐⭐⭐")
    print("OpenStreetMap (Free)    | $0.000    | ⭐⭐⭐      | ⭐⭐⭐")
    print("LLM (GPT-3.5)           | $0.002    | ⭐⭐⭐⭐     | ⭐⭐⭐")
    print("LLM (GPT-4)             | $0.030    | ⭐⭐⭐⭐⭐   | ⭐⭐⭐⭐")
    print("Ntropy (current)        | $0.020    | ⭐⭐⭐⭐⭐   | ⭐⭐⭐⭐⭐")
    print("-" * 80)


if __name__ == "__main__":
    asyncio.run(test_all_approaches())
