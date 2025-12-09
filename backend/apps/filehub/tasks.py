from config.taskiq_app import taskiq_broker

from .services import process_media_file_variants


@taskiq_broker.task
async def process_media_file_variants_task(media_file_id: str):
    """
    Асинхронная задача, которая создаёт варианты медиа-файла.
    """
    await process_media_file_variants(media_file_id)
