"""
Standardized Category Taxonomy for Transaction Categorization

This module defines the official list of categories used throughout the app.
All enrichment services should map to these categories.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Category:
    """A standardized transaction category"""
    id: str                    # Canonical ID (lowercase, snake_case)
    display_name: str          # Human-readable name
    emoji: str                 # Display emoji
    description: str           # Description for semantic matching
    keywords: List[str]        # Keywords that indicate this category
    parent: Optional[str]      # Parent category for hierarchy


# =============================================================================
# STANDARDIZED CATEGORY TAXONOMY
# =============================================================================
# These are the ONLY valid categories. All enrichment must map to one of these.

CATEGORIES: Dict[str, Category] = {
    # --- FOOD & DINING ---
    "groceries": Category(
        id="groceries",
        display_name="Groceries",
        emoji="🛒",
        description="Grocery stores, supermarkets, food shopping, wholesale clubs for food",
        keywords=["grocery", "supermarket", "food store", "market", "produce", "wholesale food"],
        parent=None
    ),
    "fast_food": Category(
        id="fast_food",
        display_name="Fast Food",
        emoji="🍔",
        description="Quick service restaurants, burger joints, pizza delivery, drive-thru",
        keywords=["fast food", "burger", "pizza", "taco", "chicken", "drive thru", "quick service"],
        parent=None
    ),
    "restaurants": Category(
        id="restaurants",
        display_name="Restaurants",
        emoji="🍽️",
        description="Sit-down dining, casual dining, fine dining, bars, pubs",
        keywords=["restaurant", "dining", "steakhouse", "bistro", "cafe", "bar", "pub", "grill"],
        parent=None
    ),
    "coffee_shops": Category(
        id="coffee_shops",
        display_name="Coffee Shops",
        emoji="☕",
        description="Coffee shops, cafes, tea houses, bakeries with coffee",
        keywords=["coffee", "cafe", "starbucks", "espresso", "latte", "tea house", "bakery"],
        parent=None
    ),

    # --- TRANSPORTATION ---
    "gas_stations": Category(
        id="gas_stations",
        display_name="Gas Stations",
        emoji="⛽",
        description="Gas stations, fuel, petrol, diesel, EV charging, car fuel",
        keywords=["gas", "fuel", "petrol", "diesel", "gasoline", "filling station", "ev charging", "costco gas"],
        parent=None
    ),
    "parking": Category(
        id="parking",
        display_name="Parking",
        emoji="🅿️",
        description="Parking lots, parking garages, meters, valet",
        keywords=["parking", "garage", "valet", "meter"],
        parent=None
    ),
    "public_transit": Category(
        id="public_transit",
        display_name="Public Transit",
        emoji="🚇",
        description="Subway, bus, metro, train, public transportation",
        keywords=["transit", "subway", "metro", "bus", "train", "rail"],
        parent=None
    ),
    "rideshare": Category(
        id="rideshare",
        display_name="Rideshare & Taxi",
        emoji="🚗",
        description="Uber, Lyft, taxi, cab, ride services",
        keywords=["uber", "lyft", "taxi", "cab", "rideshare", "ride"],
        parent=None
    ),
    "auto": Category(
        id="auto",
        display_name="Auto & Vehicles",
        emoji="🚙",
        description="Car maintenance, repairs, oil change, tires, auto parts, car wash",
        keywords=["auto", "car", "vehicle", "repair", "mechanic", "tire", "oil change", "car wash"],
        parent=None
    ),

    # --- SHOPPING ---
    "shopping": Category(
        id="shopping",
        display_name="Shopping",
        emoji="🛍️",
        description="General retail, department stores, online shopping, merchandise",
        keywords=["shopping", "retail", "store", "amazon", "merchandise", "department"],
        parent=None
    ),
    "electronics": Category(
        id="electronics",
        display_name="Electronics",
        emoji="📱",
        description="Electronics stores, computers, phones, gadgets, tech hardware",
        keywords=["electronics", "computer", "phone", "apple store", "best buy", "tech", "gadget"],
        parent=None
    ),
    "clothing": Category(
        id="clothing",
        display_name="Clothing & Apparel",
        emoji="👕",
        description="Clothing stores, fashion, shoes, accessories",
        keywords=["clothing", "apparel", "fashion", "shoes", "clothes", "wear"],
        parent=None
    ),
    "home_improvement": Category(
        id="home_improvement",
        display_name="Home Improvement",
        emoji="🔨",
        description="Hardware stores, home depot, lowes, tools, building materials",
        keywords=["home improvement", "hardware", "tools", "lumber", "home depot", "lowes"],
        parent=None
    ),

    # --- BILLS & UTILITIES ---
    "utilities": Category(
        id="utilities",
        display_name="Utilities",
        emoji="💡",
        description="Electric, water, gas utilities, trash, sewer",
        keywords=["utility", "electric", "water", "power", "energy", "trash", "sewer"],
        parent=None
    ),
    "phone_internet": Category(
        id="phone_internet",
        display_name="Phone & Internet",
        emoji="📶",
        description="Mobile phone, cell phone, internet service, cable, telecom",
        keywords=["phone", "mobile", "cell", "internet", "wifi", "broadband", "telecom", "cable", "verizon", "att", "tmobile"],
        parent=None
    ),
    "insurance": Category(
        id="insurance",
        display_name="Insurance",
        emoji="🛡️",
        description="Car insurance, health insurance, home insurance, life insurance",
        keywords=["insurance", "premium", "coverage", "policy"],
        parent=None
    ),

    # --- SUBSCRIPTIONS & SOFTWARE ---
    "software_subscriptions": Category(
        id="software_subscriptions",
        display_name="Software & Subscriptions",
        emoji="💻",
        description="Software subscriptions, SaaS, cloud services, developer tools, AI services, Claude, OpenAI, GitHub",
        keywords=["software", "subscription", "saas", "cloud", "developer", "api", "claude", "openai", "github", "cursor", "notion", "slack", "adobe", "microsoft 365"],
        parent=None
    ),
    "streaming": Category(
        id="streaming",
        display_name="Streaming Services",
        emoji="📺",
        description="Video streaming, music streaming, Netflix, Spotify, Disney+, HBO",
        keywords=["streaming", "netflix", "spotify", "disney", "hbo", "hulu", "youtube premium", "apple music", "amazon prime video"],
        parent=None
    ),
    "gaming": Category(
        id="gaming",
        display_name="Gaming",
        emoji="🎮",
        description="Video games, gaming subscriptions, PlayStation, Xbox, Steam, Nintendo",
        keywords=["gaming", "game", "playstation", "xbox", "steam", "nintendo", "twitch"],
        parent=None
    ),

    # --- HEALTH & WELLNESS ---
    "healthcare": Category(
        id="healthcare",
        display_name="Healthcare",
        emoji="🏥",
        description="Doctor visits, hospital, medical services, dentist, vision",
        keywords=["healthcare", "medical", "doctor", "hospital", "clinic", "dentist", "vision", "health"],
        parent=None
    ),
    "pharmacy": Category(
        id="pharmacy",
        display_name="Pharmacy",
        emoji="💊",
        description="Pharmacy, drugstore, prescriptions, medications, CVS, Walgreens",
        keywords=["pharmacy", "drug", "prescription", "medication", "cvs", "walgreens", "rite aid"],
        parent=None
    ),
    "fitness": Category(
        id="fitness",
        display_name="Fitness & Gym",
        emoji="🏋️",
        description="Gym membership, fitness classes, yoga, sports",
        keywords=["gym", "fitness", "workout", "yoga", "sports", "exercise"],
        parent=None
    ),
    "personal_care": Category(
        id="personal_care",
        display_name="Personal Care",
        emoji="💇",
        description="Haircut, salon, spa, beauty, grooming",
        keywords=["salon", "haircut", "spa", "beauty", "grooming", "barber", "nail"],
        parent=None
    ),

    # --- ENTERTAINMENT & RECREATION ---
    "entertainment": Category(
        id="entertainment",
        display_name="Entertainment",
        emoji="🎬",
        description="Movies, concerts, events, tickets, amusement parks",
        keywords=["entertainment", "movie", "concert", "ticket", "event", "theater", "amusement"],
        parent=None
    ),
    "travel": Category(
        id="travel",
        display_name="Travel",
        emoji="✈️",
        description="Flights, hotels, airbnb, vacation, travel bookings",
        keywords=["travel", "flight", "hotel", "airbnb", "vacation", "airline", "booking"],
        parent=None
    ),

    # --- EDUCATION ---
    "education": Category(
        id="education",
        display_name="Education",
        emoji="📚",
        description="Tuition, courses, books, school supplies, online learning",
        keywords=["education", "school", "tuition", "course", "learning", "book", "university", "college"],
        parent=None
    ),

    # --- FINANCIAL ---
    "fees_charges": Category(
        id="fees_charges",
        display_name="Fees & Charges",
        emoji="💳",
        description="Bank fees, ATM fees, service charges, late fees",
        keywords=["fee", "charge", "atm", "service charge", "late fee", "overdraft"],
        parent=None
    ),

    # --- TRANSFERS (Non-spending) ---
    "internal_transfer": Category(
        id="internal_transfer",
        display_name="Internal Transfer",
        emoji="🔄",
        description="Transfers between own accounts, savings, checking",
        keywords=["transfer", "internal", "savings", "checking", "between accounts"],
        parent=None
    ),
    "external_transfer": Category(
        id="external_transfer",
        display_name="External Transfer",
        emoji="💸",
        description="Transfers to others, Zelle, Venmo, wire transfer, ACH",
        keywords=["zelle", "venmo", "paypal", "wire", "ach", "send money"],
        parent=None
    ),
    "credit_card_payment": Category(
        id="credit_card_payment",
        display_name="Credit Card Payment",
        emoji="💳",
        description="Credit card bill payment, card payment",
        keywords=["credit card payment", "card payment", "cc payment", "pay card"],
        parent=None
    ),
    "income": Category(
        id="income",
        display_name="Income",
        emoji="💰",
        description="Salary, paycheck, direct deposit, income, refund",
        keywords=["income", "salary", "paycheck", "deposit", "refund", "payroll"],
        parent=None
    ),

    # --- CATCH-ALL ---
    "other": Category(
        id="other",
        display_name="Other",
        emoji="📦",
        description="Uncategorized transactions, miscellaneous",
        keywords=["other", "misc", "uncategorized"],
        parent=None
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_category(category_id: str) -> Optional[Category]:
    """Get a category by ID"""
    return CATEGORIES.get(category_id.lower().replace(" ", "_").replace("-", "_"))


def get_all_category_ids() -> List[str]:
    """Get list of all valid category IDs"""
    return list(CATEGORIES.keys())


def get_category_display_name(category_id: str) -> str:
    """Get display name for a category"""
    cat = get_category(category_id)
    return cat.display_name if cat else category_id.replace("_", " ").title()


def get_category_emoji(category_id: str) -> str:
    """Get emoji for a category"""
    cat = get_category(category_id)
    return cat.emoji if cat else "📦"


def normalize_category_id(raw_category: str) -> str:
    """
    Normalize a raw category string to a standard category ID.

    Examples:
        "Fast Food" -> "fast_food"
        "gas stations" -> "gas_stations"
        "software subscription" -> "software_subscriptions"
    """
    if not raw_category:
        return "other"

    normalized = raw_category.lower().strip()
    normalized = normalized.replace(" ", "_").replace("-", "_")

    # Direct match
    if normalized in CATEGORIES:
        return normalized

    # Common aliases
    ALIASES = {
        "fast_food": ["fastfood", "quick_service"],
        "gas_stations": ["gas", "gas_station", "fuel", "petrol"],
        "restaurants": ["restaurant", "dining", "dine_in"],
        "coffee_shops": ["coffee", "coffee_shop", "cafe"],
        "software_subscriptions": ["software", "subscription", "software_subscription", "saas", "cloud_services"],
        "streaming": ["video_streaming", "music_streaming", "television", "tv"],
        "groceries": ["grocery", "supermarket"],
        "shopping": ["retail", "general_merchandise"],
        "electronics": ["electronic", "tech"],
        "healthcare": ["medical", "health", "doctor"],
        "entertainment": ["movies", "events"],
        "phone_internet": ["telecom", "telecommunications", "mobile", "internet"],
        "auto": ["automotive", "car_maintenance", "vehicle"],
        "internal_transfer": ["transfer", "bank_transfer"],
        "external_transfer": ["p2p", "p2p_transfer", "peer_to_peer"],
    }

    for category_id, aliases in ALIASES.items():
        if normalized in aliases or normalized == category_id:
            return category_id

    # Partial match on keywords
    for category_id, category in CATEGORIES.items():
        for keyword in category.keywords:
            if keyword.replace(" ", "_") == normalized:
                return category_id

    return "other"


def get_categories_for_llm_prompt() -> str:
    """
    Generate a formatted string of categories for LLM prompts.

    Returns a string like:
    - groceries: Grocery stores, supermarkets, food shopping
    - fast_food: Quick service restaurants, burger joints
    ...
    """
    lines = []
    for cat_id, cat in CATEGORIES.items():
        if cat_id not in ["internal_transfer", "external_transfer", "credit_card_payment", "income"]:
            lines.append(f"- {cat_id}: {cat.description}")
    return "\n".join(lines)


# Precompute category texts for semantic matching
CATEGORY_TEXTS_FOR_EMBEDDING = {
    cat_id: f"{cat.display_name}. {cat.description}. Keywords: {', '.join(cat.keywords)}"
    for cat_id, cat in CATEGORIES.items()
}
