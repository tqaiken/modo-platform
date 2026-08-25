"""
BAGALAU — Национальная платформа оценки качества образования.
Модульный FastAPI backend.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="BAGALAU API",
    version="0.1.0",
    description="Национальная платформа оценки качества школьного образования",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Module routers ───────────────────────────────────────────────────────────

# 1. Identity & Access
from app.modules.identity.routes import router as identity_router
app.include_router(identity_router, prefix="/api/v1/auth", tags=["Identity"])

# 2. Organizations
from app.modules.organizations.routes import router as org_router
app.include_router(org_router, prefix="/api/v1/organizations", tags=["Organizations"])

# 3. Item Bank
from app.modules.item_bank.routes import router as item_bank_router
app.include_router(item_bank_router, prefix="/api/v1/questions", tags=["Item Bank"])

# 4. Review Workflow
from app.modules.review.routes import router as review_router
app.include_router(review_router, prefix="/api/v1/review", tags=["Review"])

# 5. Test Design (Blueprint + Diagnostics)
from app.modules.test_design.routes import router as test_design_router
app.include_router(test_design_router, prefix="/api/v1/diagnostics", tags=["Test Design"])

# 6. Delivery (Sessions + Answers)
from app.modules.delivery.routes import router as delivery_router
app.include_router(delivery_router, prefix="/api/v1/sessions", tags=["Delivery"])

# 7. Scoring
from app.modules.scoring.routes import router as scoring_router
app.include_router(scoring_router, prefix="/api/v1/scoring", tags=["Scoring"])

# 8. Analytics
from app.modules.analytics.routes import router as analytics_router
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])

# 9. Reporting
from app.modules.reporting.routes import router as reporting_router
app.include_router(reporting_router, prefix="/api/v1/reports", tags=["Reporting"])

# 10. Audit
from app.modules.audit.routes import router as audit_router
app.include_router(audit_router, prefix="/api/v1/audit", tags=["Audit"])


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": "BAGALAU",
        "version": "0.1.0",
    }
