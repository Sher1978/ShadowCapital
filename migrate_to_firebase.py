import asyncio
import logging
from database.connection import get_db_session
from database.models import User, ShadowLog, GlobalSettings
from database.firebase_db import FirestoreDB
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate():
    logger.info("🚀 Starting SQLite to Firestore migration...")
    
    async with get_db_session() as session:
        # 1. Migrate Global Settings
        logger.info("⚙️ Migrating Global Settings...")
        settings_stmt = select(GlobalSettings).limit(1)
        res = await session.execute(settings_stmt)
        sql_settings = res.scalar()
        if sql_settings:
            settings_dict = {
                "morning_time": sql_settings.morning_time,
                "evening_time": sql_settings.evening_time,
                "deadline_time": sql_settings.deadline_time,
                "sunday_time": sql_settings.sunday_time,
                "updated_at": datetime.utcnow()
            }
            await FirestoreDB.update_global_settings(settings_dict)
            logger.info("✅ Global Settings migrated.")

        # 2. Migrate Users
        logger.info("👤 Migrating Users...")
        user_stmt = select(User).options(joinedload(User.shadow_map))
        res = await session.execute(user_stmt)
        users = res.scalars().all()
        
        for u in users:
            logger.info(f"   - Migrating user: {u.full_name} (@{u.username})")
            user_data = {
                "tg_id": u.tg_id,
                "username": u.username,
                "full_name": u.full_name,
                "role": u.role,
                "status": u.status,
                "scenario_type": u.scenario_type,
                "sfi_index": u.sfi_index or 1.0,
                "red_flags_count": u.red_flags_count or 0,
                "last_insight": u.last_insight,
                "morning_time": u.morning_time or "09:00",
                "evening_time": u.evening_time or "21:00",
                "created_at": u.created_at or datetime.utcnow(),
                "sprint_start_date": u.sprint_start_date,
                "last_morning_sent": u.last_morning_sent,
                "last_evening_sent": u.last_evening_sent,
                "target_quality_l1": u.shadow_map.quality_name if u.shadow_map else None,
                "target_quality_l2": u.shadow_map.quality_description if u.shadow_map else None,
                "updated_at": datetime.utcnow()
            }
            await FirestoreDB.create_user(user_data)
            
            # 3. Migrate Logs for this user
            log_stmt = select(ShadowLog).where(ShadowLog.user_id == u.id)
            log_res = await session.execute(log_stmt)
            logs = log_res.scalars().all()
            
            if logs:
                logger.info(f"     + Migrating {len(logs)} logs...")
                for l in logs:
                    log_data = {
                        "user_id": str(u.tg_id),
                        "content": l.content,
                        "type": l.type,
                        "is_voice": l.is_voice,
                        "sfi_impact": l.sfi_impact,
                        "is_red_flag": l.is_red_flag,
                        "created_at": l.created_at or datetime.utcnow()
                    }
                    # We use a custom call to FirestoreDB to add legacy logs with specific timestamps
                    await FirestoreDB.db.collection("logs").add(log_data)
                    
        logger.info("✅ Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
