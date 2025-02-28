# Audio Processing & Dictation Tools

This repository contains tools for processing audio files, generating subtitles, and practicing dictation.

## Components

### 1. Audio to SRT Converter

A Python tool that automatically detects speech segments in audio files and generates SRT subtitle files with timestamps.

#### Features

- Automatically splits audio into speech segments
- Generates properly formatted SRT subtitle files
- Customizable detection parameters
- Works with various audio file formats
- Can use pre-defined content from a subtitle.txt file

#### Usage

```python
from audio_to_srt import process_audio

# Process an audio file with default settings
process_audio("your_audio_file.mp3")
```

#### Advanced Usage

```python
process_audio(
    audio_file="your_audio_file.mp3",
    output_file="custom_output.srt",  # Optional: custom output file name
    min_dur=0.5,                      # Minimum duration of speech segments
    max_dur=10,                       # Maximum duration of speech segments
    max_silence=0.3,                  # Maximum silence duration within segments
    energy_threshold=55               # Energy threshold for speech detection
)
```

### 2. Dictation Helper

An interactive GUI application that helps with dictation practice by playing audio segments from an SRT file and allowing the user to navigate between segments.

#### Features

- Load audio files and corresponding SRT subtitle files
- Navigate through audio segments (previous, replay, next)
- Convenient keyboard shortcuts for quick navigation
- Automatically saves progress between sessions
- Display subtitle text while playing audio segments

#### Usage

Run the application:

```sh
python dictation_helper.py
```

Then:
1. Select an audio file
2. Select a corresponding SRT file
3. Use the buttons or keyboard shortcuts to navigate through segments

#### Keyboard Shortcuts

- **Enter**: Play next segment
- **Shift+Space**: Replay current segment
- **Ctrl+Left Arrow**: Play previous segment

## Requirements

- Python 3.6+
- auditok library
- pygame
- PyQt5
- keyboard

## Installation

Install the required dependencies:

```sh
pip install -r requirements.txt
```

## Workflow

1. Use audio_to_srt.py to process an audio file and generate an SRT file with timestamps
2. Optionally prepare a subtitle.txt file with content for each segment
3. Use dictation_helper.py to practice listening and dictation with the processed audio

## Progress Tracking

The Dictation Helper automatically saves your progress in dictation_progress.json and will restore your position when you reopen the application.