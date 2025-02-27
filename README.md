# Audio to SRT Converter

A Python tool that automatically detects speech segments in audio files and generates SRT subtitle files with timestamps.

## Features

- Automatically splits audio into speech segments
- Generates properly formatted SRT subtitle files
- Customizable detection parameters
- Works with various audio file formats

## Requirements

- Python 3.6+
- auditok library (v0.2.0 or higher)

## Installation

Install the required dependencies:

```sh
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from audio_to_srt import process_audio

# Process an audio file with default settings
process_audio("your_audio_file.mp3")
```

### Advanced Usage

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

## Parameters

- **audio_file**: Path to the input audio file
- **output_file**: Path for the output SRT file (optional)
- **min_dur**: Minimum duration (in seconds) for a valid speech segment
- **max_dur**: Maximum duration (in seconds) for a speech segment
- **max_silence**: Maximum silence duration (in seconds) within a speech segment
- **energy_threshold**: Energy level threshold for speech detection

## Output

The script generates an SRT file with timestamps for each detected speech segment. The actual transcript content is initially set to "xxx" and needs to be filled in manually.
