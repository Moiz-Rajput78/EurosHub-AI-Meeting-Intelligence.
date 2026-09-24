# Meeting Intelligence

AI-powered meeting transcription and intelligent notes system built with FastAPI, React, TypeScript, Faster Whisper, Pyannote, FFmpeg, and Ollama Cloud.

Meeting Intelligence allows users to upload recorded meetings, automatically transcribe the entire conversation, detect speakers, generate structured AI meeting intelligence, review and correct transcripts, search conversations, and export the results.

---

## Features

### Meeting Upload

Upload recorded meetings in supported audio and video formats:

- MP3
- WAV
- M4A
- MP4
- WEBM

Uploaded media is validated and processed securely by the backend.

---

## Audio and Video Processing

FFmpeg and FFprobe are used to:

- validate uploaded media
- detect audio streams
- inspect media metadata
- extract audio from video
- normalize recordings
- convert audio to mono
- convert audio to 16 kHz PCM WAV for transcription

---

## Automatic Transcription

Meeting Intelligence uses Faster Whisper to generate a complete timestamped transcript.

Features include:

- full meeting transcription
- segment-level timestamps
- detected language
- editable transcript segments
- original transcript text preservation

The transcript is never replaced with a summary.

---

## Speaker Diarization

Pyannote Audio is used to detect speaker turns.

The application automatically generates labels such as:

- Speaker 1
- Speaker 2
- Speaker 3

Users can rename detected speakers when their identities are known.

If speaker diarization fails, transcript processing can still continue without speaker labels.

---

## AI Meeting Intelligence

The system uses Ollama Cloud for structured meeting analysis.

Current model:

```text
gemma4:cloud