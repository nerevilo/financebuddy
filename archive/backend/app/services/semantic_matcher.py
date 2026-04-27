"""
Semantic Matching for Intelligent Transaction Categorization

Uses FastEmbed (ONNX-based) for lightweight, fast embeddings without PyTorch.
This is the industry standard for production deployments - ~50x smaller than
sentence-transformers and optimized for CPU inference.

Key Features:
1. Pre-computes embeddings for all categories and known merchants
2. Uses cosine similarity to find best matches
3. Handles edge cases like "Costco Gas" vs "Costco Groceries"
4. Falls back gracefully if ML libraries unavailable
"""
import re
from typing import Dict, Optional, Tuple
from ..core.logging_config import get_logger
from .categories import (
    CATEGORY_TEXTS_FOR_EMBEDDING
)

logger = get_logger(__name__)

# Try to import fastembed (lightweight ONNX-based embeddings)
try:
    from fastembed import TextEmbedding
    import numpy as np
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False
    TextEmbedding = None
    np = None
    logger.warning(
        "fastembed not installed. Run: pip install fastembed. "
        "Falling back to rule-based matching."
    )


class SemanticMatcher:
    """
    Intelligent transaction categorization using semantic similarity.

    Uses FastEmbed (ONNX-based) to embed transaction descriptions and find
    the most semantically similar category. Much lighter than PyTorch-based
    alternatives - ideal for production/serverless deployments.
    """

    # Model to use - BGE-small is fast, accurate, and lightweight
    # See: https://github.com/qdrant/fastembed#supported-models
    MODEL_NAME = "BAAI/bge-small-en-v1.5"

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.65
    MEDIUM_CONFIDENCE_THRESHOLD = 0.45

    def __init__(self):
        self.model = None
        self.category_embeddings = None
        self.merchant_embeddings = None
        self._initialized = False

        # Known merchants with their categories (for high-precision matching)
        # Format: "search_text": ("merchant_name", "category_id", priority)
        # Higher priority = check first (for specificity)
        self.known_merchants: Dict[str, Tuple[str, str, int]] = {}
        self._build_merchant_database()

        # Initialize model lazily
        if FASTEMBED_AVAILABLE:
            self._initialize_model()

    def _initialize_model(self):
        """Initialize the FastEmbed model and pre-compute embeddings"""
        if self._initialized:
            return

        try:
            logger.info(f"Loading semantic model: {self.MODEL_NAME}")
            self.model = TextEmbedding(model_name=self.MODEL_NAME)

            # Pre-compute category embeddings
            category_texts = list(CATEGORY_TEXTS_FOR_EMBEDDING.values())
            category_ids = list(CATEGORY_TEXTS_FOR_EMBEDDING.keys())

            # FastEmbed returns a generator, convert to list of arrays
            category_embeds = list(self.model.embed(category_texts))
            self.category_embeddings = {
                cat_id: np.array(embedding)
                for cat_id, embedding in zip(category_ids, category_embeds)
            }

            # Pre-compute merchant embeddings for known merchants
            merchant_texts = list(self.known_merchants.keys())
            if merchant_texts:
                merchant_embeds = list(self.model.embed(merchant_texts))
                self.merchant_embeddings = {
                    text: np.array(embedding)
                    for text, embedding in zip(merchant_texts, merchant_embeds)
                }

            self._initialized = True
            logger.info(f"Semantic matcher initialized with {len(self.category_embeddings)} categories, {len(self.merchant_embeddings or {})} merchants")

        except Exception as e:
            logger.error(f"Failed to initialize semantic matcher: {e}")
            self._initialized = False

    def _build_merchant_database(self):
        """
        Build database of known merchants with their categories.

        Priority levels:
        - 100+: Very specific (e.g., "COSTCO GAS")
        - 50-99: Specific modifiers (e.g., "SHELL GAS")
        - 1-49: General merchants (e.g., "COSTCO")
        """
        # =================================================================
        # HIGH PRIORITY: Specific variants (check these FIRST)
        # =================================================================

        # Gas stations at retail locations (MUST come before general retail)
        self._add_merchant("COSTCO GAS", "Costco Gas", "gas_stations", 150)
        self._add_merchant("COSTCO GASOLINE", "Costco Gas", "gas_stations", 150)
        self._add_merchant("COSTCO FUEL", "Costco Gas", "gas_stations", 150)
        self._add_merchant("SAMS CLUB GAS", "Sam's Club Gas", "gas_stations", 150)
        self._add_merchant("SAM'S CLUB GAS", "Sam's Club Gas", "gas_stations", 150)
        self._add_merchant("SAMS CLUB FUEL", "Sam's Club Gas", "gas_stations", 150)
        self._add_merchant("SAM'S CLUB FUEL", "Sam's Club Gas", "gas_stations", 150)  # With apostrophe
        self._add_merchant("WALMART GAS", "Walmart Gas", "gas_stations", 150)
        self._add_merchant("WALMART FUEL", "Walmart Gas", "gas_stations", 150)
        self._add_merchant("KROGER FUEL", "Kroger Fuel Center", "gas_stations", 150)
        self._add_merchant("KROGER GAS", "Kroger Fuel Center", "gas_stations", 150)
        self._add_merchant("BJS GAS", "BJ's Gas", "gas_stations", 150)
        self._add_merchant("BJ'S GAS", "BJ's Gas", "gas_stations", 150)

        # =================================================================
        # SOFTWARE & TECH SUBSCRIPTIONS
        # =================================================================
        self._add_merchant("CLAUDE", "Claude (Anthropic)", "software_subscriptions", 100)
        self._add_merchant("ANTHROPIC", "Anthropic", "software_subscriptions", 100)
        self._add_merchant("OPENAI", "OpenAI", "software_subscriptions", 100)
        self._add_merchant("CHATGPT", "ChatGPT (OpenAI)", "software_subscriptions", 100)
        self._add_merchant("CURSOR", "Cursor", "software_subscriptions", 100)
        self._add_merchant("GITHUB", "GitHub", "software_subscriptions", 100)
        self._add_merchant("GITLAB", "GitLab", "software_subscriptions", 100)
        self._add_merchant("NOTION", "Notion", "software_subscriptions", 100)
        self._add_merchant("SLACK", "Slack", "software_subscriptions", 100)
        self._add_merchant("FIGMA", "Figma", "software_subscriptions", 100)
        self._add_merchant("ADOBE", "Adobe", "software_subscriptions", 100)
        self._add_merchant("MICROSOFT 365", "Microsoft 365", "software_subscriptions", 100)
        self._add_merchant("OFFICE 365", "Microsoft 365", "software_subscriptions", 100)
        self._add_merchant("MSFT", "Microsoft", "software_subscriptions", 90)
        self._add_merchant("DROPBOX", "Dropbox", "software_subscriptions", 100)
        self._add_merchant("GOOGLE WORKSPACE", "Google Workspace", "software_subscriptions", 100)
        self._add_merchant("GOOGLE ONE", "Google One", "software_subscriptions", 100)
        self._add_merchant("ICLOUD", "iCloud", "software_subscriptions", 100)
        self._add_merchant("APPLE.COM/BILL", "Apple Services", "software_subscriptions", 100)
        self._add_merchant("DIGITALOCEAN", "DigitalOcean", "software_subscriptions", 100)
        self._add_merchant("AWS", "Amazon Web Services", "software_subscriptions", 100)
        self._add_merchant("HEROKU", "Heroku", "software_subscriptions", 100)
        self._add_merchant("VERCEL", "Vercel", "software_subscriptions", 100)
        self._add_merchant("NETLIFY", "Netlify", "software_subscriptions", 100)
        self._add_merchant("RAILWAY", "Railway", "software_subscriptions", 100)
        self._add_merchant("SUPABASE", "Supabase", "software_subscriptions", 100)
        self._add_merchant("MONGODB", "MongoDB", "software_subscriptions", 100)
        self._add_merchant("1PASSWORD", "1Password", "software_subscriptions", 100)
        self._add_merchant("LASTPASS", "LastPass", "software_subscriptions", 100)
        self._add_merchant("BITWARDEN", "Bitwarden", "software_subscriptions", 100)
        self._add_merchant("NORDVPN", "NordVPN", "software_subscriptions", 100)
        self._add_merchant("EXPRESSVPN", "ExpressVPN", "software_subscriptions", 100)
        self._add_merchant("JETBRAINS", "JetBrains", "software_subscriptions", 100)
        self._add_merchant("REPLIT", "Replit", "software_subscriptions", 100)
        self._add_merchant("COPILOT", "GitHub Copilot", "software_subscriptions", 100)
        self._add_merchant("CHATGPT PLUS", "ChatGPT Plus", "software_subscriptions", 110)  # Higher priority than CHATGPT
        self._add_merchant("CLAUDE PRO", "Claude Pro", "software_subscriptions", 100)
        self._add_merchant("MIDJOURNEY", "Midjourney", "software_subscriptions", 100)
        self._add_merchant("CANVA", "Canva", "software_subscriptions", 100)
        self._add_merchant("GRAMMARLY", "Grammarly", "software_subscriptions", 100)
        self._add_merchant("ZOOM", "Zoom", "software_subscriptions", 100)
        self._add_merchant("CALENDLY", "Calendly", "software_subscriptions", 100)
        self._add_merchant("ZAPIER", "Zapier", "software_subscriptions", 100)
        self._add_merchant("AIRTABLE", "Airtable", "software_subscriptions", 100)
        self._add_merchant("LINEAR", "Linear", "software_subscriptions", 100)
        self._add_merchant("JIRA", "Jira", "software_subscriptions", 100)
        self._add_merchant("ATLASSIAN", "Atlassian", "software_subscriptions", 100)
        self._add_merchant("TWILIO", "Twilio", "software_subscriptions", 100)
        self._add_merchant("SENDGRID", "SendGrid", "software_subscriptions", 100)
        self._add_merchant("MAILCHIMP", "Mailchimp", "software_subscriptions", 100)

        # =================================================================
        # STREAMING SERVICES
        # =================================================================
        self._add_merchant("NETFLIX", "Netflix", "streaming", 100)
        self._add_merchant("SPOTIFY", "Spotify", "streaming", 100)
        self._add_merchant("APPLE MUSIC", "Apple Music", "streaming", 100)
        self._add_merchant("DISNEY+", "Disney+", "streaming", 100)
        self._add_merchant("DISNEY +", "Disney+", "streaming", 100)
        self._add_merchant("DISNEYPLUS", "Disney+", "streaming", 100)
        self._add_merchant("DISNEY PLUS", "Disney+", "streaming", 100)
        self._add_merchant("HULU", "Hulu", "streaming", 100)
        self._add_merchant("HBO MAX", "Max (HBO)", "streaming", 100)
        self._add_merchant("HBO", "HBO", "streaming", 90)
        self._add_merchant("MAX.COM", "Max (HBO)", "streaming", 100)
        self._add_merchant("AMAZON PRIME", "Amazon Prime", "streaming", 100)
        self._add_merchant("PRIME VIDEO", "Prime Video", "streaming", 100)
        self._add_merchant("YOUTUBE PREMIUM", "YouTube Premium", "streaming", 100)
        self._add_merchant("YOUTUBE MUSIC", "YouTube Music", "streaming", 100)
        self._add_merchant("PEACOCK", "Peacock", "streaming", 100)
        self._add_merchant("PARAMOUNT+", "Paramount+", "streaming", 100)
        self._add_merchant("PARAMOUNT PLUS", "Paramount+", "streaming", 100)
        self._add_merchant("APPLE TV", "Apple TV+", "streaming", 100)
        self._add_merchant("APPLETV", "Apple TV+", "streaming", 100)
        self._add_merchant("CRUNCHYROLL", "Crunchyroll", "streaming", 100)
        self._add_merchant("AUDIBLE", "Audible", "streaming", 100)
        self._add_merchant("PANDORA", "Pandora", "streaming", 100)
        self._add_merchant("TIDAL", "Tidal", "streaming", 100)
        self._add_merchant("DEEZER", "Deezer", "streaming", 100)
        self._add_merchant("SIRIUSXM", "SiriusXM", "streaming", 100)
        self._add_merchant("SIRIUS XM", "SiriusXM", "streaming", 100)

        # =================================================================
        # GAMING
        # =================================================================
        self._add_merchant("STEAM", "Steam", "gaming", 100)
        self._add_merchant("PLAYSTATION", "PlayStation", "gaming", 100)
        self._add_merchant("XBOX", "Xbox", "gaming", 100)
        self._add_merchant("NINTENDO", "Nintendo", "gaming", 100)
        self._add_merchant("EPIC GAMES", "Epic Games", "gaming", 100)
        self._add_merchant("RIOT GAMES", "Riot Games", "gaming", 100)
        self._add_merchant("BLIZZARD", "Blizzard", "gaming", 100)
        self._add_merchant("EA.COM", "Electronic Arts", "gaming", 100)
        self._add_merchant("ROBLOX", "Roblox", "gaming", 100)
        self._add_merchant("TWITCH", "Twitch", "gaming", 100)
        self._add_merchant("DISCORD", "Discord", "gaming", 90)  # Could also be software

        # =================================================================
        # GAS STATIONS (Standard)
        # =================================================================
        self._add_merchant("SHELL", "Shell", "gas_stations", 80)
        self._add_merchant("EXXON", "ExxonMobil", "gas_stations", 80)
        self._add_merchant("EXXONMOBIL", "ExxonMobil", "gas_stations", 85)
        self._add_merchant("MOBIL", "Mobil", "gas_stations", 80)
        self._add_merchant("CHEVRON", "Chevron", "gas_stations", 80)
        self._add_merchant("BP", "BP", "gas_stations", 80)
        self._add_merchant("MARATHON", "Marathon", "gas_stations", 80)
        self._add_merchant("SUNOCO", "Sunoco", "gas_stations", 80)
        self._add_merchant("CIRCLE K", "Circle K", "gas_stations", 80)
        self._add_merchant("7-ELEVEN", "7-Eleven", "gas_stations", 70)  # Also convenience
        self._add_merchant("7 ELEVEN", "7-Eleven", "gas_stations", 70)
        self._add_merchant("WAWA", "Wawa", "gas_stations", 70)
        self._add_merchant("SHEETZ", "Sheetz", "gas_stations", 70)
        self._add_merchant("SPEEDWAY", "Speedway", "gas_stations", 80)
        self._add_merchant("RACETRAC", "RaceTrac", "gas_stations", 80)
        self._add_merchant("QUIKTRIP", "QuikTrip", "gas_stations", 80)
        self._add_merchant("QT ", "QuikTrip", "gas_stations", 80)
        self._add_merchant("PILOT", "Pilot Flying J", "gas_stations", 80)
        self._add_merchant("LOVES", "Love's Travel Stop", "gas_stations", 80)
        self._add_merchant("LOVE'S", "Love's Travel Stop", "gas_stations", 80)
        self._add_merchant("CASEY", "Casey's", "gas_stations", 70)
        self._add_merchant("MURPHY USA", "Murphy USA", "gas_stations", 80)
        self._add_merchant("MURPHYUSA", "Murphy USA", "gas_stations", 80)
        self._add_merchant("PHILLIPS 66", "Phillips 66", "gas_stations", 80)
        self._add_merchant("CONOCO", "Conoco", "gas_stations", 80)
        self._add_merchant("VALERO", "Valero", "gas_stations", 80)
        self._add_merchant("ARCO", "ARCO", "gas_stations", 80)
        self._add_merchant("CITGO", "Citgo", "gas_stations", 80)
        self._add_merchant("SINCLAIR", "Sinclair", "gas_stations", 80)
        self._add_merchant("GULF", "Gulf", "gas_stations", 80)
        self._add_merchant("TEXACO", "Texaco", "gas_stations", 80)
        self._add_merchant("GETGO", "GetGo", "gas_stations", 80)
        self._add_merchant("KUM & GO", "Kum & Go", "gas_stations", 80)
        self._add_merchant("KWIK TRIP", "Kwik Trip", "gas_stations", 80)
        self._add_merchant("MAVERIK", "Maverik", "gas_stations", 80)
        self._add_merchant("THORNTONS", "Thorntons", "gas_stations", 80)
        self._add_merchant("ROYAL FARMS", "Royal Farms", "gas_stations", 70)

        # =================================================================
        # GROCERIES
        # =================================================================
        self._add_merchant("COSTCO", "Costco", "groceries", 50)  # Lower than COSTCO GAS
        self._add_merchant("WALMART", "Walmart", "groceries", 50)
        self._add_merchant("TARGET", "Target", "groceries", 50)
        self._add_merchant("KROGER", "Kroger", "groceries", 50)
        self._add_merchant("PUBLIX", "Publix", "groceries", 60)
        self._add_merchant("SAFEWAY", "Safeway", "groceries", 60)
        self._add_merchant("WHOLE FOODS", "Whole Foods", "groceries", 60)
        self._add_merchant("TRADER JOE", "Trader Joe's", "groceries", 60)
        self._add_merchant("ALDI", "Aldi", "groceries", 60)
        self._add_merchant("SAM'S CLUB", "Sam's Club", "groceries", 50)
        self._add_merchant("SAMS CLUB", "Sam's Club", "groceries", 50)
        self._add_merchant("LIDL", "Lidl", "groceries", 60)
        self._add_merchant("WEGMANS", "Wegmans", "groceries", 60)
        self._add_merchant("HEB", "H-E-B", "groceries", 60)
        self._add_merchant("H-E-B", "H-E-B", "groceries", 60)
        self._add_merchant("FOOD LION", "Food Lion", "groceries", 60)
        self._add_merchant("GIANT", "Giant", "groceries", 60)
        self._add_merchant("STOP & SHOP", "Stop & Shop", "groceries", 60)
        self._add_merchant("HARRIS TEETER", "Harris Teeter", "groceries", 60)
        self._add_merchant("MEIJER", "Meijer", "groceries", 60)
        self._add_merchant("WINCO", "WinCo", "groceries", 60)
        self._add_merchant("SPROUTS", "Sprouts", "groceries", 60)
        self._add_merchant("PIGGLY WIGGLY", "Piggly Wiggly", "groceries", 60)
        self._add_merchant("FRESH MARKET", "The Fresh Market", "groceries", 60)
        self._add_merchant("MARKET BASKET", "Market Basket", "groceries", 60)

        # =================================================================
        # FAST FOOD
        # =================================================================
        self._add_merchant("MCDONALD", "McDonald's", "fast_food", 80)
        self._add_merchant("BURGER KING", "Burger King", "fast_food", 80)
        self._add_merchant("WENDY", "Wendy's", "fast_food", 80)
        self._add_merchant("TACO BELL", "Taco Bell", "fast_food", 80)
        self._add_merchant("CHICK-FIL-A", "Chick-fil-A", "fast_food", 80)
        self._add_merchant("CHICKFILA", "Chick-fil-A", "fast_food", 80)
        self._add_merchant("KFC", "KFC", "fast_food", 80)
        self._add_merchant("POPEYES", "Popeyes", "fast_food", 80)
        self._add_merchant("DOMINO", "Domino's", "fast_food", 80)
        self._add_merchant("PIZZA HUT", "Pizza Hut", "fast_food", 80)
        self._add_merchant("PAPA JOHN", "Papa John's", "fast_food", 80)
        self._add_merchant("LITTLE CAESARS", "Little Caesars", "fast_food", 80)
        self._add_merchant("SUBWAY", "Subway", "fast_food", 80)
        self._add_merchant("JIMMY JOHN", "Jimmy John's", "fast_food", 80)
        self._add_merchant("JERSEY MIKE", "Jersey Mike's", "fast_food", 80)
        self._add_merchant("FIREHOUSE SUBS", "Firehouse Subs", "fast_food", 80)
        self._add_merchant("ARBY", "Arby's", "fast_food", 80)
        self._add_merchant("SONIC", "Sonic", "fast_food", 80)
        self._add_merchant("DAIRY QUEEN", "Dairy Queen", "fast_food", 80)
        self._add_merchant("HARDEE", "Hardee's", "fast_food", 80)
        self._add_merchant("CARL'S JR", "Carl's Jr.", "fast_food", 80)
        self._add_merchant("IN-N-OUT", "In-N-Out", "fast_food", 80)
        self._add_merchant("FIVE GUYS", "Five Guys", "fast_food", 80)
        self._add_merchant("SHAKE SHACK", "Shake Shack", "fast_food", 80)
        self._add_merchant("WHATABURGER", "Whataburger", "fast_food", 80)
        self._add_merchant("CULVER", "Culver's", "fast_food", 80)
        self._add_merchant("JACK IN THE BOX", "Jack in the Box", "fast_food", 80)
        self._add_merchant("DEL TACO", "Del Taco", "fast_food", 80)
        self._add_merchant("CHIPOTLE", "Chipotle", "fast_food", 80)
        self._add_merchant("QDOBA", "Qdoba", "fast_food", 80)
        self._add_merchant("MOE'S", "Moe's Southwest", "fast_food", 80)
        self._add_merchant("PANDA EXPRESS", "Panda Express", "fast_food", 80)
        self._add_merchant("PANERA", "Panera Bread", "fast_food", 75)
        self._add_merchant("CAVA", "Cava", "fast_food", 75)
        self._add_merchant("SWEETGREEN", "Sweetgreen", "fast_food", 75)
        self._add_merchant("WINGSTOP", "Wingstop", "fast_food", 80)
        self._add_merchant("BUFFALO WILD WINGS", "Buffalo Wild Wings", "fast_food", 75)
        self._add_merchant("ZAXBY", "Zaxby's", "fast_food", 80)
        self._add_merchant("RAISING CANE", "Raising Cane's", "fast_food", 80)
        self._add_merchant("COOKOUT", "Cook Out", "fast_food", 80)
        self._add_merchant("CHECKERS", "Checkers", "fast_food", 80)
        self._add_merchant("RALLYS", "Rally's", "fast_food", 80)

        # =================================================================
        # COFFEE SHOPS
        # =================================================================
        self._add_merchant("STARBUCKS", "Starbucks", "coffee_shops", 80)
        self._add_merchant("DUNKIN", "Dunkin'", "coffee_shops", 80)
        self._add_merchant("PEET'S", "Peet's Coffee", "coffee_shops", 80)
        self._add_merchant("PEETS", "Peet's Coffee", "coffee_shops", 80)
        self._add_merchant("DUTCH BROS", "Dutch Bros", "coffee_shops", 80)
        self._add_merchant("TIM HORTONS", "Tim Hortons", "coffee_shops", 80)
        self._add_merchant("CARIBOU COFFEE", "Caribou Coffee", "coffee_shops", 80)
        self._add_merchant("COFFEE BEAN", "Coffee Bean", "coffee_shops", 80)
        self._add_merchant("PHILZ", "Philz Coffee", "coffee_shops", 80)
        self._add_merchant("BLUE BOTTLE", "Blue Bottle", "coffee_shops", 80)
        self._add_merchant("INTELLIGENTSIA", "Intelligentsia", "coffee_shops", 80)
        self._add_merchant("LA COLOMBE", "La Colombe", "coffee_shops", 80)
        self._add_merchant("SCOOTER'S COFFEE", "Scooter's Coffee", "coffee_shops", 80)
        self._add_merchant("BIGGBY", "Biggby Coffee", "coffee_shops", 80)
        self._add_merchant("GREGORYS", "Gregory's Coffee", "coffee_shops", 80)

        # =================================================================
        # PHARMACY
        # =================================================================
        self._add_merchant("CVS", "CVS", "pharmacy", 80)
        self._add_merchant("WALGREENS", "Walgreens", "pharmacy", 80)
        self._add_merchant("RITE AID", "Rite Aid", "pharmacy", 80)

        # =================================================================
        # RIDESHARE & TRANSIT
        # =================================================================
        self._add_merchant("UBER", "Uber", "rideshare", 80)
        self._add_merchant("LYFT", "Lyft", "rideshare", 80)
        self._add_merchant("UBER EATS", "Uber Eats", "fast_food", 85)  # Food delivery
        self._add_merchant("DOORDASH", "DoorDash", "fast_food", 85)
        self._add_merchant("GRUBHUB", "Grubhub", "fast_food", 85)
        self._add_merchant("POSTMATES", "Postmates", "fast_food", 85)
        self._add_merchant("INSTACART", "Instacart", "groceries", 85)

        # =================================================================
        # SHOPPING / RETAIL
        # =================================================================
        self._add_merchant("AMAZON", "Amazon", "shopping", 60)
        self._add_merchant("AMZN", "Amazon", "shopping", 60)
        self._add_merchant("BEST BUY", "Best Buy", "electronics", 80)
        self._add_merchant("HOME DEPOT", "Home Depot", "home_improvement", 80)
        self._add_merchant("LOWE'S", "Lowe's", "home_improvement", 80)
        self._add_merchant("LOWES", "Lowe's", "home_improvement", 80)
        self._add_merchant("MENARDS", "Menards", "home_improvement", 80)
        self._add_merchant("ACE HARDWARE", "Ace Hardware", "home_improvement", 80)
        self._add_merchant("IKEA", "IKEA", "shopping", 70)
        self._add_merchant("BED BATH", "Bed Bath & Beyond", "shopping", 70)
        self._add_merchant("WAYFAIR", "Wayfair", "shopping", 70)
        self._add_merchant("APPLE STORE", "Apple Store", "electronics", 80)
        self._add_merchant("APPLE.COM", "Apple", "electronics", 70)

        # =================================================================
        # TRAVEL
        # =================================================================
        self._add_merchant("AIRBNB", "Airbnb", "travel", 90)
        self._add_merchant("VRBO", "VRBO", "travel", 90)
        self._add_merchant("MARRIOTT", "Marriott", "travel", 90)
        self._add_merchant("HILTON", "Hilton", "travel", 90)
        self._add_merchant("HYATT", "Hyatt", "travel", 90)
        self._add_merchant("IHG", "IHG", "travel", 90)
        self._add_merchant("EXPEDIA", "Expedia", "travel", 90)
        self._add_merchant("BOOKING.COM", "Booking.com", "travel", 90)
        self._add_merchant("HOTELS.COM", "Hotels.com", "travel", 90)
        self._add_merchant("SOUTHWEST", "Southwest Airlines", "travel", 90)
        self._add_merchant("DELTA", "Delta Airlines", "travel", 90)
        self._add_merchant("UNITED", "United Airlines", "travel", 90)
        self._add_merchant("AMERICAN AIRLINES", "American Airlines", "travel", 90)
        self._add_merchant("JETBLUE", "JetBlue", "travel", 90)
        self._add_merchant("FRONTIER", "Frontier Airlines", "travel", 90)
        self._add_merchant("SPIRIT", "Spirit Airlines", "travel", 90)

        # =================================================================
        # FITNESS
        # =================================================================
        self._add_merchant("PLANET FITNESS", "Planet Fitness", "fitness", 90)
        self._add_merchant("LA FITNESS", "LA Fitness", "fitness", 90)
        self._add_merchant("24 HOUR FITNESS", "24 Hour Fitness", "fitness", 90)
        self._add_merchant("EQUINOX", "Equinox", "fitness", 90)
        self._add_merchant("ORANGETHEORY", "Orangetheory", "fitness", 90)
        self._add_merchant("CROSSFIT", "CrossFit", "fitness", 90)
        self._add_merchant("YMCA", "YMCA", "fitness", 90)
        self._add_merchant("PELOTON", "Peloton", "fitness", 90)
        self._add_merchant("CLASSPASS", "ClassPass", "fitness", 90)

        # =================================================================
        # PHONE & INTERNET
        # =================================================================
        self._add_merchant("VERIZON", "Verizon", "phone_internet", 90)
        self._add_merchant("AT&T", "AT&T", "phone_internet", 90)
        self._add_merchant("ATT", "AT&T", "phone_internet", 90)
        self._add_merchant("T-MOBILE", "T-Mobile", "phone_internet", 90)
        self._add_merchant("TMOBILE", "T-Mobile", "phone_internet", 90)
        self._add_merchant("SPRINT", "Sprint", "phone_internet", 90)
        self._add_merchant("COMCAST", "Comcast/Xfinity", "phone_internet", 90)
        self._add_merchant("XFINITY", "Xfinity", "phone_internet", 90)
        self._add_merchant("SPECTRUM", "Spectrum", "phone_internet", 90)
        self._add_merchant("COX", "Cox Communications", "phone_internet", 90)
        self._add_merchant("GOOGLE FI", "Google Fi", "phone_internet", 90)
        self._add_merchant("MINT MOBILE", "Mint Mobile", "phone_internet", 90)
        self._add_merchant("VISIBLE", "Visible", "phone_internet", 90)
        self._add_merchant("US CELLULAR", "US Cellular", "phone_internet", 90)
        self._add_merchant("CRICKET", "Cricket Wireless", "phone_internet", 90)
        self._add_merchant("METRO BY T-MOBILE", "Metro by T-Mobile", "phone_internet", 90)
        self._add_merchant("BOOST MOBILE", "Boost Mobile", "phone_internet", 90)
        self._add_merchant("STARLINK", "Starlink", "phone_internet", 90)

    def _add_merchant(self, search_text: str, merchant_name: str, category_id: str, priority: int):
        """Add a merchant to the database"""
        self.known_merchants[search_text.upper()] = (merchant_name, category_id, priority)

    def _clean_description(self, description: str) -> str:
        """Clean transaction description for matching"""
        # Remove common prefixes
        prefixes = [
            "Debit Card Purchase - ",
            "Credit Card Purchase - ",
            "Online Purchase - ",
            "POS ",
            "ATM ",
            "ACH ",
            "Withdrawal from ",
            "Payment to ",
            "Recurring ",
        ]

        cleaned = description
        for prefix in prefixes:
            if cleaned.upper().startswith(prefix.upper()):
                cleaned = cleaned[len(prefix):]
                break

        # Remove store numbers and location info for cleaner matching
        # But keep it in a separate variable if needed
        cleaned = cleaned.strip()

        return cleaned

    def match_merchant_rules(self, description: str) -> Optional[Dict]:
        """
        Rule-based merchant matching with priority ordering.

        Checks more specific patterns first (higher priority).

        Returns:
            {
                "merchant": "Costco Gas",
                "category": "gas_stations",
                "confidence": 0.95,
                "source": "rule_match",
                "matched_pattern": "COSTCO GAS"
            }
        """
        cleaned = self._clean_description(description)
        desc_upper = cleaned.upper()

        # Sort merchants by priority (highest first)
        sorted_merchants = sorted(
            self.known_merchants.items(),
            key=lambda x: x[1][2],  # Sort by priority
            reverse=True
        )

        for pattern, (merchant_name, category_id, priority) in sorted_merchants:
            # Use word boundary matching to avoid false positives
            # e.g., "MOBIL" shouldn't match "MOBILE"
            # Handle special characters in patterns (like DISNEY+)
            escaped_pattern = re.escape(pattern)
            # For patterns ending with special chars, use looser matching
            if pattern.endswith('+') or pattern.endswith('$'):
                pattern_regex = r'\b' + escaped_pattern
            else:
                pattern_regex = r'\b' + escaped_pattern + r'\b'
            if re.search(pattern_regex, desc_upper):
                # Higher priority = higher confidence
                confidence = min(0.70 + (priority / 500), 0.98)

                return {
                    "merchant": merchant_name,
                    "category": category_id,
                    "confidence": confidence,
                    "source": "rule_match",
                    "matched_pattern": pattern
                }

        return None

    def match_semantic(self, description: str) -> Optional[Dict]:
        """
        Semantic matching using FastEmbed embeddings.

        Embeds the transaction description and finds the most similar category.

        Returns:
            {
                "merchant": None,  # Semantic match doesn't identify merchant
                "category": "gas_stations",
                "confidence": 0.72,
                "source": "semantic_match",
                "similarity_score": 0.72
            }
        """
        if not self._initialized or not self.model:
            return None

        try:
            cleaned = self._clean_description(description)

            # Embed the description (FastEmbed returns generator)
            desc_embedding = np.array(list(self.model.embed([cleaned]))[0])

            # Find most similar category
            best_category = None
            best_similarity = -1

            for cat_id, cat_embedding in self.category_embeddings.items():
                # Cosine similarity
                similarity = np.dot(desc_embedding, cat_embedding) / (
                    np.linalg.norm(desc_embedding) * np.linalg.norm(cat_embedding)
                )

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_category = cat_id

            if best_category and best_similarity >= self.MEDIUM_CONFIDENCE_THRESHOLD:
                return {
                    "merchant": None,
                    "category": best_category,
                    "confidence": float(best_similarity),
                    "source": "semantic_match",
                    "similarity_score": float(best_similarity)
                }

        except Exception as e:
            logger.error(f"Semantic matching error: {e}")

        return None

    def match(self, description: str) -> Optional[Dict]:
        """
        Main matching method - tries rules first, then semantic.

        Returns:
            {
                "merchant": "Costco Gas" or None,
                "category": "gas_stations",
                "confidence": 0.95,
                "source": "rule_match" or "semantic_match"
            }
        """
        # Try rule-based matching first (fast, high precision)
        rule_result = self.match_merchant_rules(description)
        if rule_result and rule_result["confidence"] >= 0.70:
            return rule_result

        # Fall back to semantic matching
        semantic_result = self.match_semantic(description)
        if semantic_result:
            return semantic_result

        # If semantic matching not available or failed, return rule result even if low confidence
        if rule_result:
            return rule_result

        return None


# Singleton instance for efficiency (model loading is expensive)
_semantic_matcher_instance: Optional[SemanticMatcher] = None


def get_semantic_matcher() -> SemanticMatcher:
    """Get the singleton semantic matcher instance"""
    global _semantic_matcher_instance
    if _semantic_matcher_instance is None:
        _semantic_matcher_instance = SemanticMatcher()
    return _semantic_matcher_instance
