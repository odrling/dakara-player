"""Manage audio files independently of the media player."""

import pathlib

import filetype


def get_audio_files(filepath: pathlib.Path) -> list[pathlib.Path]:
    """Get audio files with the same name as provided file.

    Args:
        filepath (pathlib.Path): Path of the initial file.

    Returns:
        list of pathlib.Path: List of paths of audio files.
    """
    audio_file = filepath.with_suffix(".mka")
    if audio_file.exists():
        return [audio_file]

    return []


def is_audio_file(file_path):
    """Detect if a file is audio file based on standard magic numbers.

    Args:
        file_path (pathlib.Path): Path of the file to investigate.

    Returns:
        bool: `True` if the file is an audio file, `False` otherwise.
    """
    kind = filetype.guess(str(file_path))
    if not kind:
        return False

    maintype, _ = kind.mime.split("/")

    return maintype == "audio"
