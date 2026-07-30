"""
Seed script: creates test users and initial subjects.
Run: python -m app.seed
"""
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.subject import Subject


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Subjects ──
        subjects = [
            {"code": "reading", "title": "Чтение", "title_kz": "Оқу"},
            {"code": "math", "title": "Математика", "title_kz": "Математика"},
            {"code": "science", "title": "Естествознание", "title_kz": "Жаратылыстану"},
            {"code": "history", "title": "История", "title_kz": "Тарих"},
            {"code": "language", "title": "Язык", "title_kz": "Тіл"},
        ]

        for s in subjects:
            existing = db.query(Subject).filter(Subject.code == s["code"]).first()
            if not existing:
                db.add(Subject(**s))
        db.commit()
        print(f"✓ Subjects seeded ({len(subjects)} items)")

        # ── Users ──
        users = [
            {
                "email": "curator@testforge.kz",
                "full_name": "Админ Куратор",
                "password": "curator123",
                "role": UserRole.CURATOR,
            },
            {
                "email": "verifier@testforge.kz",
                "full_name": "Верификатор Тестов",
                "password": "verifier123",
                "role": UserRole.VERIFIER,
            },
            {
                "email": "developer@testforge.kz",
                "full_name": "Разработчик Вопросов",
                "password": "developer123",
                "role": UserRole.DEVELOPER,
            },
        ]

        for u in users:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                db.add(User(
                    email=u["email"],
                    full_name=u["full_name"],
                    hashed_password=hash_password(u["password"]),
                    role=u["role"],
                ))
        db.commit()
        print(f"✓ Users seeded ({len(users)} accounts)")

        print("\nTest credentials:")
        print("  Curator:    curator@testforge.kz / curator123")
        print("  Verifier:   verifier@testforge.kz / verifier123")
        print("  Developer:  developer@testforge.kz / developer123")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
