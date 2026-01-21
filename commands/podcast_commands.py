import time
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger
from pydantic import BaseModel

# Note: For the Supabase job queue implementation, we'll define the command as a regular function
# and the job_queue system will handle the background execution

from open_notebook.config import DATA_FOLDER
from open_notebook.database.repository import repo_query
from open_notebook.podcasts.models import EpisodeProfile, PodcastEpisode, SpeakerProfile

try:
    from podcast_creator import configure, create_podcast
except ImportError as e:
    logger.error(f"Failed to import podcast_creator: {e}")
    raise ValueError("podcast_creator library not available")


async def generate_podcast_command(
    episode_profile_name: str,
    episode_name: str,
    content: str,
    briefing_suffix: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a podcast using the podcast-creator library with Episode Profiles.
    """
    start_time = time.time()
    episode = None
    try:
        logger.info(f"Starting podcast generation for episode: {episode_name}")
        logger.info(f"Using episode profile: {episode_profile_name}")

        episode_profile = await EpisodeProfile.get_by_name(episode_profile_name)
        if not episode_profile:
            raise ValueError(f"Episode profile '{episode_profile_name}' not found")

        speaker_profile = await SpeakerProfile.get_by_name(
            episode_profile.speaker_config
        )
        if not speaker_profile:
            raise ValueError(
                f"Speaker profile '{episode_profile.speaker_config}' not found"
            )

        episode = PodcastEpisode(
            name=episode_name,
            episode_profile=episode_profile.model_dump(),
            speaker_profile=speaker_profile.model_dump(),
            briefing=episode_profile.default_briefing + (f"\n\nAdditional instructions: {briefing_suffix}" if briefing_suffix else ""),
            content=content,
            status="starting",
        )
        await episode.save()

        episode_profiles = await EpisodeProfile.get_all()
        speaker_profiles = await SpeakerProfile.get_all()

        episode_profiles_dict = {p.name: p.model_dump() for p in episode_profiles}
        speaker_profiles_dict = {p.name: p.model_dump() for p in speaker_profiles}
        
        configure("speakers_config", {"profiles": speaker_profiles_dict})
        configure("episode_config", {"profiles": episode_profiles_dict})

        output_dir = Path(f"{DATA_FOLDER}/podcasts/episodes/{episode_name}")
        output_dir.mkdir(parents=True, exist_ok=True)

        episode.status = "generating"
        await episode.save()

        result = await create_podcast(
            content=content,
            briefing=episode.briefing,
            episode_name=episode_name,
            output_dir=str(output_dir),
            speaker_config=speaker_profile.name,
            episode_profile=episode_profile.name,
        )

        episode.audio_file = str(result.get("final_output_file_path"))
        episode.transcript = result.get("transcript")
        episode.outline = result.get("outline")
        episode.status = "completed"
        await episode.save()

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully generated podcast episode: {episode.id} in {processing_time:.2f}s"
        )

        return {
            "success": True,
            "episode_id": episode.id,
            "audio_file_path": episode.audio_file,
            "processing_time": processing_time,
        }

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Podcast generation failed: {e}")
        
        if episode:
            episode.status = "failed"
            await episode.save()

        return {
            "success": False, 
            "processing_time": processing_time, 
            "error_message": str(e)
        }
