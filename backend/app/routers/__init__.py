from .auth import router as auth_router
from .accounts import router as accounts_router
from .transactions import router as transactions_router
from .analytics import router as analytics_router
from .teller_connect import router as teller_router
from .categorization import router as categorization_router
from .dashboard import router as dashboard_router
from .institutions import router as institutions_router
from .goals import router as goals_router
from .income import router as income_router
from .insights import router as insights_router
from .profile import router as profile_router
from .anomalies import router as anomalies_router
from .tags import router as tags_router

__all__ = [
    "auth_router",
    "accounts_router",
    "transactions_router",
    "analytics_router",
    "teller_router",
    "categorization_router",
    "dashboard_router",
    "institutions_router",
    "goals_router",
    "income_router",
    "insights_router",
    "profile_router",
    "anomalies_router",
    "tags_router"
]
