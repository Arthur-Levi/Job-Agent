from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(254),unique=True,index=True)
    password_hash:Mapped[str]=mapped_column(String(300))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class Session(Base):
    __tablename__='sessions'
    token_hash:Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
class Profile(Base):
    __tablename__='profiles'
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    name:Mapped[str]=mapped_column(String(120),default='')
    target_role:Mapped[str]=mapped_column(String(120),default='')
    current_salary_cents:Mapped[int|None]=mapped_column(Integer,nullable=True)
    target_salary_cents:Mapped[int|None]=mapped_column(Integer,nullable=True)
    hours_per_week:Mapped[int]=mapped_column(Integer,default=5)
    location:Mapped[str]=mapped_column(String(160),default='')
    summary:Mapped[str]=mapped_column(Text,default='')
class Evidence(Base):
    __tablename__='evidence'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    kind:Mapped[str]=mapped_column(String(30))
    title:Mapped[str]=mapped_column(String(160))
    description:Mapped[str]=mapped_column(Text)
    url:Mapped[str]=mapped_column(String(1000),default='')
    status:Mapped[str]=mapped_column(String(30),default='DECLARED')
    verification_note:Mapped[str]=mapped_column(Text,default='')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class Job(Base):
    __tablename__='jobs'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    title:Mapped[str]=mapped_column(String(160))
    company:Mapped[str]=mapped_column(String(160))
    description:Mapped[str]=mapped_column(Text)
    requirements_json:Mapped[str]=mapped_column(Text,default='[]')
    source_url:Mapped[str]=mapped_column(String(1000),default='')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class Application(Base):
    __tablename__='applications'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    job_id:Mapped[int]=mapped_column(ForeignKey('jobs.id',ondelete='CASCADE'))
    status:Mapped[str]=mapped_column(String(30),default='saved')
    notes:Mapped[str]=mapped_column(Text,default='')
    __table_args__=(UniqueConstraint('user_id','job_id',name='uq_application_user_job'),)
class Task(Base):
    __tablename__='tasks'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    title:Mapped[str]=mapped_column(String(300))
    done:Mapped[bool]=mapped_column(Boolean,default=False)
class Subscription(Base):
    __tablename__='subscriptions'
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    stripe_customer_id:Mapped[str|None]=mapped_column(String(120),nullable=True,unique=True)
    stripe_subscription_id:Mapped[str|None]=mapped_column(String(120),nullable=True,unique=True)
    status:Mapped[str]=mapped_column(String(40),default='inactive')
    stripe_price_id:Mapped[str|None]=mapped_column(String(120),nullable=True)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
class WebhookEvent(Base):
    __tablename__='webhook_events'
    id:Mapped[str]=mapped_column(String(150),primary_key=True)
    processed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class Audit(Base):
    __tablename__='audit'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'),nullable=True,index=True)
    action:Mapped[str]=mapped_column(String(100))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

# Persistent career evidence graph and longitudinal decision history.
class EvidenceLink(Base):
    __tablename__='evidence_links'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    evidence_id:Mapped[int]=mapped_column(ForeignKey('evidence.id',ondelete='CASCADE'),index=True)
    requirement:Mapped[str]=mapped_column(String(160))
    relation:Mapped[str]=mapped_column(String(30),default='SUPPORTS')
    rationale:Mapped[str]=mapped_column(Text,default='')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    __table_args__=(UniqueConstraint('user_id','evidence_id','requirement',name='uq_graph_edge'),)

class CareerSnapshot(Base):
    __tablename__='career_snapshots'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    fingerprint:Mapped[str]=mapped_column(String(64))
    metrics_json:Mapped[str]=mapped_column(Text)
    recommendations_json:Mapped[str]=mapped_column(Text)
    explanation_json:Mapped[str]=mapped_column(Text)

class CareerOutcome(Base):
    __tablename__='career_outcomes'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    kind:Mapped[str]=mapped_column(String(30))
    description:Mapped[str]=mapped_column(Text,default='')
    job_id:Mapped[int|None]=mapped_column(ForeignKey('jobs.id',ondelete='SET NULL'),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class EvidenceAssessment(Base):
    __tablename__='evidence_assessments'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    evidence_id:Mapped[int]=mapped_column(ForeignKey('evidence.id',ondelete='CASCADE'),index=True)
    rubric_version:Mapped[str]=mapped_column(String(40))
    submission_json:Mapped[str]=mapped_column(Text)
    result_json:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class ArtifactReview(Base):
    __tablename__='artifact_reviews'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    evidence_id:Mapped[int]=mapped_column(ForeignKey('evidence.id',ondelete='CASCADE'),index=True)
    review_version:Mapped[str]=mapped_column(String(40))
    inventory_sha256:Mapped[str]=mapped_column(String(64))
    result_json:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)


class MasterProfileItem(Base):
    __tablename__='master_profile_items'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    category:Mapped[str]=mapped_column(String(30))
    title:Mapped[str]=mapped_column(String(180))
    organization:Mapped[str]=mapped_column(String(180),default='')
    start_date:Mapped[str]=mapped_column(String(10),default='')
    end_date:Mapped[str]=mapped_column(String(10),default='')
    description:Mapped[str]=mapped_column(Text,default='')
    source_evidence_id:Mapped[int|None]=mapped_column(ForeignKey('evidence.id',ondelete='SET NULL'),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class CareerFact(Base):
    __tablename__='career_facts'
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    subject:Mapped[str]=mapped_column(String(180))
    predicate:Mapped[str]=mapped_column(String(80))
    value:Mapped[str]=mapped_column(Text)
    source_type:Mapped[str]=mapped_column(String(40))
    source_reference:Mapped[str]=mapped_column(String(300),default='')
    verification:Mapped[str]=mapped_column(String(40),default='USER_DECLARED')
    status:Mapped[str]=mapped_column(String(20),default='ACTIVE')
    supersedes_id:Mapped[int|None]=mapped_column(ForeignKey('career_facts.id',ondelete='SET NULL'),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
