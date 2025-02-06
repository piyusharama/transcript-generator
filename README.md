# Transcript Generator

## Overview
The **Transcript Generator** is a Python-based GUI application that allows users to extract audio from video files, transcribe the speech using OpenAI's Whisper model, and optionally analyze the transcript using OpenAI's GPT models.

## Features
- **Select Video/Audio**: Users can select a media file (video/audio) for processing.
- **Extract Audio**: Automatically extracts audio from video files.
- **Generate Transcripts**: Uses Whisper AI to transcribe the extracted audio.
- **Analyze Transcripts** (Optional): Uses OpenAI's GPT API to analyze the generated transcript.
- **View Reports**: Open the generated transcript and analysis report in a text editor.
- **Cancel Processing**: Allows users to cancel the process at any stage.
- **Simple & Interactive GUI**: Built using Tkinter for ease of use.

## Prerequisites
Ensure the following dependencies are installed:

### System Requirements
- Python 3.8+
- Windows, macOS, or Linux

### Required Python Packages
Install the required dependencies using:
```sh
pip install torch openai whisper moviepy tkinter
```

## Usage

1. **Run the application**:
   ```sh
   python transcript_generator.py
   ```

2. **Select a video/audio file** to process.
3. Click **"Generate Transcript"** to start the transcription process.
4. (Optional) Check **"Analyze Transcript"**, enter an **OpenAI API Key**, and provide a **prompt** for further analysis.
5. Once completed, click **"Open Report"** to view the transcript/analysis.
6. Click **"Close"** to exit the application.

## Directory Structure
When processing a file, the following directory structure is created:
```
/media_folder/
  ├── input_video.mp4
  ├── input_video.mp3  (Extracted audio)
  ├── input_video.txt  (Transcript)
  ├── input_video_report.txt  (Analysis Report - Optional)
```

## Notes
- The Whisper model automatically selects "medium" if a GPU is available, otherwise, it uses "base".
- On Windows, Notepad is used to open text files, on macOS, TextEdit is used, and on Linux, Gedit is used.
- OpenAI API key is required for analysis but not for transcription.

## License
This project is created by **Piyush Sharma**. Feel free to modify and use it for personal and educational purposes.

