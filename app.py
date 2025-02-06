import tkinter as tk
from tkinter import filedialog, messagebox
import os
import platform
import subprocess
from pathlib import Path

import whisper
import torch
from moviepy.video.io.VideoFileClip import VideoFileClip
from openai import OpenAI


def open_file_in_text_editor(file_path: Path):
    """
    Cross-platform helper to explicitly open the file in a known text editor
    rather than the system’s default (which might launch LibreOffice, etc.).
    """
    try:
        system = platform.system()
        if system == "Windows":
            # Force Notepad on Windows
            subprocess.run(["notepad", str(file_path)])
        elif system == "Darwin":  # macOS
            # Force TextEdit on macOS
            subprocess.run(["open", "-a", "TextEdit", str(file_path)])
        else:
            # Force Gedit on Linux (adjust if you use Kate, Nano, etc.)
            subprocess.run(["gedit", str(file_path)])
    except Exception as e:
        print(f"Error opening file in text editor: {e}")


class TranscriptApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transcript Generator")

        # Cancel/close logic
        self.should_cancel = False
        self.protocol("WM_DELETE_WINDOW", self.on_close_window)

        self.file_path = None
        self.generated_report_path = None

        # Frames
        self.top_frame = tk.Frame(self, padx=10, pady=5)
        self.top_frame.pack(fill=tk.X)

        self.mid_frame = tk.Frame(self, padx=10, pady=5)
        self.mid_frame.pack(fill=tk.X)

        self.bottom_frame = tk.Frame(self, padx=10, pady=5)
        self.bottom_frame.pack(fill=tk.BOTH, expand=True)

        # Build GUI
        self.create_widgets()

    def create_widgets(self):
        # Top row: "Select Video/Audio" + "Analyze Transcript"
        self.select_btn = tk.Button(self.top_frame, text="Select Video/Audio", command=self.select_file)
        self.select_btn.pack(side=tk.LEFT, padx=(0, 20))

        self.analyze_var = tk.BooleanVar(value=False)
        self.analyze_check = tk.Checkbutton(
            self.top_frame, text="Analyze Transcript", variable=self.analyze_var,
            command=self.toggle_analysis
        )
        self.analyze_check.pack(side=tk.LEFT)

        # Mid: API Key & Prompt (hidden if not analyzing)
        self.api_label = tk.Label(self.mid_frame, text="OpenAI API Key:")
        self.api_entry = tk.Entry(self.mid_frame, show="*", width=40)

        self.prompt_label = tk.Label(self.mid_frame, text="Prompt:")
        self.prompt_text = tk.Text(self.mid_frame, width=60, height=4)

        # "Generate Transcript" + "Cancel/Close" + "Open Report"
        self.generate_btn = tk.Button(self.mid_frame, text="Generate Transcript", command=self.run_process)
        self.generate_btn.pack(side=tk.LEFT, pady=(10,5))

        self.cancel_btn = tk.Button(self.mid_frame, text="Cancel", command=self.cancel_process)
        self.cancel_btn.pack(side=tk.LEFT, padx=10, pady=(10,5))

        self.open_report_btn = tk.Button(self.mid_frame, text="Open Report", command=self.open_report)
        # Hidden until a report is created

        # Bottom: status/log area
        self.log_text = tk.Text(self.bottom_frame, width=80, height=12)
        self.log_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.watermark_label = tk.Label(self.bottom_frame, text="Created by Piyush Sharma", anchor="e")
        self.watermark_label.pack(side=tk.BOTTOM, anchor="e")

        self.toggle_analysis()  # hide API fields initially

    def toggle_analysis(self):
        """Show/hide API Key & Prompt if 'Analyze Transcript' is checked."""
        if self.analyze_var.get():
            self.api_label.pack(anchor="w")
            self.api_entry.pack(anchor="w", pady=(0,5))
            self.prompt_label.pack(anchor="w")
            self.prompt_text.pack(anchor="w", pady=(0,5))
        else:
            self.api_label.pack_forget()
            self.api_entry.pack_forget()
            self.prompt_label.pack_forget()
            self.prompt_text.pack_forget()

    def select_file(self):
        """Choose a video or audio file."""
        path = filedialog.askopenfilename(
            title="Select Video/Audio",
            filetypes=[
                ("Video/Audio Files", "*.mp4 *.avi *.mkv *.mov *.flv *.wmv *.mp3 *.wav *.flac *.aac *.ogg *.m4a"),
                ("All Files", "*.*")
            ]
        )
        if path:
            self.file_path = path
            self.log(f"Selected media: {path}")

    def run_process(self):
        if not self.file_path:
            messagebox.showerror("Error", "Please select a video/audio file first.")
            return

        self.should_cancel = False
        self.generated_report_path = None
        self.log_text.delete("1.0", tk.END)
        self.log("Processing started...")

        input_path = Path(self.file_path)
        stem = input_path.stem
        out_dir = input_path.parent / stem
        out_dir.mkdir(exist_ok=True)

        audio_path = out_dir / f"{stem}.mp3"
        transcript_path = out_dir / f"{stem}.txt"
        report_path = out_dir / f"{stem}_report.txt"

        # Step 1: skip or extract
        if not self.skip_extract_audio(input_path, audio_path):
            return

        # Step 2: skip or transcribe
        transcript = self.skip_transcribe_audio(audio_path, transcript_path)
        if transcript is None:
            return

        # Step 3: skip or analyze
        if self.analyze_var.get():
            api_key = self.api_entry.get().strip()
            user_prompt = self.prompt_text.get("1.0", tk.END).strip()
            if self.skip_analyze(transcript, report_path, api_key, user_prompt):
                self.generated_report_path = report_path
                self.open_report_btn.pack(side=tk.LEFT, padx=10, pady=(10,5))

        self.log("Processing complete.")
        # Convert "Cancel" → "Close"
        self.cancel_btn.config(text="Close", command=self.close_app)

    ###############################
    # Step 1: Extract audio
    ###############################
    def skip_extract_audio(self, input_path, audio_path):
        if audio_path.exists():
            self.log(f"Skipping audio extraction; {audio_path.name} exists.")
            return True

        if self.should_cancel:
            self.log("Canceled before extraction started.")
            return False

        exts_audio = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}
        if input_path.suffix.lower() in exts_audio:
            self.log("Input is audio; copying as .mp3")
            try:
                os.system(f'cp "{input_path}" "{audio_path}"')
            except Exception as e:
                self.log(f"Error copying audio: {e}")
                return False
            return True

        self.log("Extracting audio from video...")
        try:
            clip = VideoFileClip(str(input_path))
            clip.audio.write_audiofile(str(audio_path))
        except Exception as e:
            self.log(f"Error extracting audio: {e}")
            return False

        if self.should_cancel:
            self.log("Canceled after extraction.")
            return False

        self.log(f"Audio extracted to {audio_path.name}")
        return True

    ###############################
    # Step 2: Transcribe
    ###############################
    def skip_transcribe_audio(self, audio_path, transcript_path):
        if transcript_path.exists():
            self.log(f"Skipping transcription; {transcript_path.name} exists.")
            try:
                return transcript_path.read_text(encoding="utf-8")
            except Exception as e:
                self.log(f"Error reading existing transcript: {e}")
                return None

        if self.should_cancel:
            self.log("Canceled before transcription.")
            return None

        self.log("Transcribing with Whisper (auto model selection).")
        model_name = "medium" if torch.cuda.is_available() else "base"
        self.log(f"Using model: {model_name}")

        try:
            model = whisper.load_model(model_name)
            result = model.transcribe(str(audio_path))
            transcript = result["text"]
        except Exception as e:
            self.log(f"Error during transcription: {e}")
            return None

        if self.should_cancel:
            self.log("Canceled after transcription.")
            return None

        try:
            transcript_path.write_text(transcript, encoding="utf-8")
            self.log(f"Transcript saved to {transcript_path.name}")
        except Exception as e:
            self.log(f"Error saving transcript: {e}")
            return None

        return transcript

    ###############################
    # Step 3: Analyze
    ###############################
    def skip_analyze(self, transcript, report_path, api_key, user_prompt):
        if not api_key:
            self.log("No API key. Skipping analysis.")
            return False

        if report_path.exists():
            self.log(f"Skipping analysis; {report_path.name} exists.")
            return False

        if self.should_cancel:
            self.log("Canceled before analysis.")
            return False

        self.log("Analyzing transcript with gpt-4o-mini...")
        client = OpenAI(api_key=api_key)
        prompt_data = f"{user_prompt}\n\nTranscript:\n{transcript}"

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt_data}],
                max_tokens=4400,
                temperature=0.7
            )
            analysis = response.choices[0].message.content
            self.log("Analysis result:\n" + analysis)
            report_path.write_text(analysis, encoding="utf-8")
            self.log(f"Analysis report saved to {report_path.name}")
            return True
        except Exception as e:
            self.log(f"OpenAI Error: {e}")
            return False

    ###############################
    # Cancel / Close
    ###############################
    def cancel_process(self):
        self.should_cancel = True
        self.log("Cancel requested... next step is halted after finishing the current one.")

    def close_app(self):
        self.log("Closing application.")
        self.destroy()

    def on_close_window(self):
        self.log("Window closed by OS.")
        self.should_cancel = True
        self.destroy()

    ###############################
    # "Open Report" → text editor
    ###############################
    def open_report(self):
        if self.generated_report_path and self.generated_report_path.exists():
            self.log(f"Opening report: {self.generated_report_path}")
            open_file_in_text_editor(self.generated_report_path)
        else:
            self.log("No report file found to open!")

    ###############################
    # Logging helper
    ###############################
    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.update()


def main():
    app = TranscriptApp()
    app.mainloop()

if __name__ == "__main__":
    main()
    