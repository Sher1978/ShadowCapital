from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey, DateTime, Text, Float, select, func
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String)
    role = Column(String, default="client")  # client, admin
    status = Column(String, default="new")  # new, pending, active, rejected
    shadow_map_id = Column(Integer, ForeignKey("shadow_maps.id"), nullable=True)
    timezone = Column(String, default="UTC")
    sprint_start_date = Column(DateTime, nullable=True) # Date when the 30-day sprint actually begins
    morning_time = Column(String, default="08:00")
    evening_time = Column(String, default="20:00")
    target_quality_l1 = Column(String, nullable=True)
    scenario_type = Column(String, nullable=True)
    shadow_map_link = Column(String, nullable=True)
    red_flags_count = Column(Integer, default=0)
    # Consent
    rules_accepted = Column(Boolean, default=False)
    rules_accepted_at = Column(DateTime, nullable=True)
    last_insight = Column(Text, nullable=True)
    sfi_index = Column(Float, default=1.0)
    last_morning_sent = Column(DateTime, nullable=True)
    last_evening_sent = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    shadow_map = relationship("ShadowMap", back_populates="users")
    logs = relationship("ShadowLog", back_populates="user")

class ShadowMap(Base):
    __tablename__ = "shadow_maps"

    id = Column(Integer, primary_key=True)
    quality_name = Column(String, nullable=False)
    potential_desc = Column(Text)
    
    users = relationship("User", back_populates="shadow_map")

class ShadowLog(Base):
    __tablename__ = "shadow_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text)
    is_sabotage = Column(Boolean, default=False)
    sabotage_marker = Column(String, nullable=True) # e.g., "avoidance", "somatic"
    is_voice = Column(Boolean, default=False)
    file_id = Column(String, nullable=True) # Telegram file_id for voice/audio
    local_file_path = Column(String, nullable=True) # Path in /media/audio/
    analysis_reason = Column(Text, nullable=True) # Internal AI analysis
    sfi_score = Column(Float, nullable=True) # Friction Index
    feedback_to_client = Column(Text, nullable=True) # Direct feedback from AI
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="logs")

class AdminLog(Base):
    __tablename__ = "admin_logs"
    
    id = Column(Integer, primary_key=True)
    admin_id = Column(BigInteger, nullable=False)
    action = Column(String, nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class GlobalSettings(Base):
    __tablename__ = "global_settings"
    
    id = Column(Integer, primary_key=True)
    morning_time = Column(String, default="09:00")
    deadline_time = Column(String, default="20:30")
    evening_time = Column(String, default="21:30")
    sunday_time = Column(String, default="18:00")

    @classmethod
    async def get_settings(cls, session):
        stmt = select(cls).where(cls.id == 1)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        if not settings:
            settings = cls(id=1)
            session.add(settings)
            await session.commit()
        return settings
