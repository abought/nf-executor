from sqlalchemy.orm import Session

from src.db import enums, models, serializers


def get_workflows(db: Session,
                  skip: int = 0, limit: int = 100):
    return db.query(models.Workflow).offset(skip).limit(limit).all()


def get_jobs(db: Session, workflow_id = None, status: enums.JobStatus = None,
             skip: int = 0, limit: int = 100):
    queryset = db.query(models.Job).order_by(models.Job.cr)

    if workflow_id is not None:
        queryset.filter(models.Job.workflow_id == workflow_id)

    if status is not None:
        queryset.filter(models.Job.status == status.value)

    return queryset.offset(skip).limit(limit).all()

# def get_user(db: Session, user_id: int):
#     return db.query(models.User).filter(models.User.id == user_id).first()
#
#
# def get_user_by_email(db: Session, email: str):
#     return db.query(models.User).filter(models.User.email == email).first()
#
#
# def get_users(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.User).offset(skip).limit(limit).all()
#
#
# def create_user(db: Session, user: serializers.UserCreate):
#     fake_hashed_password = user.password + "notreallyhashed"
#     db_user = models.User(email=user.email, hashed_password=fake_hashed_password)
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#     return db_user
#
#
# def get_items(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.Item).offset(skip).limit(limit).all()
#
#
# def create_user_item(db: Session, item: serializers.ItemCreate, user_id: int):
#     db_item = models.Item(**item.dict(), owner_id=user_id)
#     db.add(db_item)
#     db.commit()
#     db.refresh(db_item)
#     return db_item
