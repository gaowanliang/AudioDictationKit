import os
import datetime
from auditok import split


def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    time_obj = datetime.timedelta(seconds=seconds)
    hours, remainder = divmod(time_obj.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(time_obj.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def generate_srt(audio_regions, output_file):
    """Generate SRT file based on audio regions"""
    # Try to read subtitle.txt file
    subtitles = []
    subtitle_file = "subtitle.txt"
    try:
        with open(subtitle_file, "r", encoding="utf-8") as sf:
            subtitles = [line.strip() for line in sf.readlines() if line.strip()]
        print(f"Successfully loaded {len(subtitles)} subtitles")
    except FileNotFoundError:
        print(f"Subtitle file not found: {subtitle_file}, will use 'xxx' as default")

    with open(output_file, "w", encoding="utf-8") as f:
        for i, region in enumerate(audio_regions):
            # Index number
            f.write(f"{i+1}\n")
            # Timestamp
            start_time = format_timestamp(region.meta.start)
            end_time = format_timestamp(region.meta.end)
            f.write(f"{start_time} --> {end_time}\n")
            # Subtitle content (use subtitle.txt content or "xxx" if not enough)
            subtitle_text = subtitles[i] if i < len(subtitles) else "xxx"
            f.write(f"{subtitle_text}\n\n")

    # Output actual subtitle count information
    regions_count = len(audio_regions)
    subtitles_count = len(subtitles)
    if subtitles_count < regions_count:
        print(
            f"Not enough subtitles: {regions_count} audio regions, but only {subtitles_count} subtitle lines. {regions_count - subtitles_count} regions using default 'xxx'"
        )
    elif subtitles_count > regions_count:
        print(
            f"Too many subtitles: {regions_count} audio regions, but {subtitles_count} subtitle lines. {subtitles_count - regions_count} subtitle lines unused"
        )
    else:
        print(
            f"Perfect match: {regions_count} audio regions and {subtitles_count} subtitle lines"
        )


def process_audio(
    audio_file,
    output_file=None,
    min_dur=0.5,
    max_dur=10,
    max_silence=0.3,
    energy_threshold=10,
):
    # Determine output file path
    if output_file is None:
        base_name = os.path.splitext(audio_file)[0]
        output_file = f"{base_name}.srt"

    print(f"Processing audio file: {audio_file}")
    print(f"Min duration: {min_dur}s")
    print(f"Max duration: {max_dur}s")
    print(f"Max silence: {max_silence}s")
    print(f"Energy threshold: {energy_threshold}")

    # Split audio
    audio_regions = list(
        split(
            audio_file,
            min_dur=min_dur,
            max_dur=max_dur,
            max_silence=max_silence,
            energy_threshold=energy_threshold,
        )
    )

    # Print segmentation info
    print(f"Found {len(audio_regions)} audio segments")
    for i, region in enumerate(audio_regions):
        print(
            f"Region {i+1}: {region.meta.start:.3f}s - {region.meta.end:.3f}s = {region.duration:.3f}s"
        )

    # Generate SRT file
    generate_srt(audio_regions, output_file)
    print(f"SRT file saved to: {output_file}")


if __name__ == "__main__":
    # Execute with default parameters
    audio_file = "Section 4.mp3"  # Replace with your audio file path
    process_audio(audio_file)
