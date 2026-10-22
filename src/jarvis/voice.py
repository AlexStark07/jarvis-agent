import os
import io

class VoiceProvider:
    """Abstract/fallback provider for voice operations."""

    def transcribe(self, audio_data: bytes) -> str:
        """Convert audio bytes to text."""
        # For offline/local without external credentials, return a dummy string or parse a simple header if it was a simulated test
        if os.environ.get("LIVE_TEST") == "1" and os.environ.get("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                client = OpenAI()
                # Create a file-like object and name it to satisfy OpenAI's requirements
                audio_file = io.BytesIO(audio_data)
                audio_file.name = "audio.wav"
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                return transcript.text
            except Exception as e:
                return f"Transcription error: {str(e)}"

        return "Simulated voice input text"

    def synthesize(self, text: str) -> bytes:
        """Convert text to audio bytes."""
        if os.environ.get("LIVE_TEST") == "1" and os.environ.get("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                client = OpenAI()
                response = client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=text
                )
                return response.content
            except Exception as e:
                return f"Speech generation error: {str(e)}".encode('utf-8')

        return b"Simulated voice audio bytes for: " + text.encode('utf-8')

voice_provider = VoiceProvider()
