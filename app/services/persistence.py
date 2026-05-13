import logging
from app.database import AsyncSessionLocal
from app.models.interaction import Interaction

logger = logging.getLogger(__name__)

async def log_interaction(
    request_id: str,
    model: str,
    user_message: str,
    verdict: str,
    final_response: str,
    policy_reason: str = None,
    metadata: dict = None
):
    """
    Asynchronously logs an interaction to the database.
    Does not raise exceptions to avoid breaking the main request flow.
    """
    try:
        async with AsyncSessionLocal() as session:
            interaction = Interaction(
                request_id=request_id,
                model=model,
                user_message=user_message,
                verdict=verdict,
                policy_reason=policy_reason,
                final_response=final_response,
                metadata_json=metadata
            )
            session.add(interaction)
            await session.commit()
            logger.info(f"Logged interaction {request_id} to database.")
    except Exception as e:
        logger.error(f"Failed to log interaction {request_id}: {e}", exc_info=True)
