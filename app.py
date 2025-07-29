import os
import sys
import queue
import json
import tempfile
import asyncio
import time
import gc
import io
import threading

import pandas as pd
import sounddevice as sd
import vosk

import chromadb
from sentence_transformers import SentenceTransformer
import edge_tts
from pydub import AudioSegment
import pygame


# === Configuration ===

EXCEL_PATH = r"C:\Users\mysel\OneDrive\Pictures\310\Merged_File_with_Sheets.xlsx"
PERSIST_DIRECTORY = r"C:\Users\mysel\OneDrive\Pictures\310\chroma_db"
COLLECTION_NAME = "qna_collection"

VOSK_MODEL_PATH = r"C:\Users\mysel\OneDrive\Pictures\310\vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000

EDGE_VOICE = "en-US-JennyNeural"  # You can change the voice if you want

# Greeting message
GREETING_MESSAGE = "Hello! I'm your Bigship voice assistant. How can I help you today?"


def upload_excel_to_chroma(client, model):
    print("Uploading Excel data to ChromaDB...")

    # Delete collection if exists (optional)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = client.create_collection(COLLECTION_NAME)
    print(f"Created collection '{COLLECTION_NAME}'")

    excel_file = pd.ExcelFile(EXCEL_PATH)
    all_questions = []
    all_answers = []

    for sheet_name in excel_file.sheet_names:
        print(f"Processing sheet: {sheet_name}")
        df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
        # Extract Question (col 0), ignore col 1, Answer (col 2)
        df_slice = df.iloc[:, [0, 2]].dropna()
        questions = df_slice.iloc[:, 0].astype(str).tolist()
        answers = df_slice.iloc[:, 1].astype(str).tolist()
        all_questions.extend(questions)
        all_answers.extend(answers)

    print(f"Total Q&A pairs extracted: {len(all_questions)}")

    print("Generating embeddings for questions...")
    embeddings = model.encode(all_questions, show_progress_bar=True)

    for idx, (q, a, emb) in enumerate(zip(all_questions, all_answers, embeddings)):
        collection.add(
            ids=[str(idx)],
            documents=[q],
            metadatas=[{"answer": a}],
            embeddings=[emb.tolist()]
        )

    print(f"Uploaded {len(all_questions)} Q&A pairs successfully.")
    # No explicit persist() call needed; handled automatically

    return collection


def get_existing_collection(client):
    # Return the existing collection if present and non-empty, else None
    try:
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        if count > 0:
            print(f"Found existing collection '{COLLECTION_NAME}' with {count} entries.")
            return collection
        else:
            print(f"Collection '{COLLECTION_NAME}' exists but is empty.")
            return None
    except Exception:
        print(f"Collection '{COLLECTION_NAME}' does not exist.")
        return None


def play_audio_from_memory(audio_data):
    """Play audio from memory using pygame mixer"""
    try:
        # Initialize pygame mixer
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        
        # Create a temporary file in memory
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        # Load and play the audio
        pygame.mixer.music.load(temp_file_path)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        
        # Clean up
        pygame.mixer.music.unload()
        pygame.mixer.quit()
        
        # Remove temporary file
        try:
            os.remove(temp_file_path)
        except:
            pass
            
    except Exception as e:
        print(f"Error playing audio: {e}")


def run_voice_assistant(collection, embedder):
    q_audio = queue.Queue()
    vosk_model = vosk.Model(VOSK_MODEL_PATH)
    
    # Global flag to control audio input
    listening_active = True
    audio_lock = threading.Lock()

    def audio_callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        if listening_active:
            q_audio.put(bytes(indata))

    async def speak_text(text):
        nonlocal listening_active
        
        # Pause listening while speaking
        with audio_lock:
            listening_active = False
        
        try:
            # Generate TTS audio in memory
            communicate = edge_tts.Communicate(text, EDGE_VOICE)
            
            # Get audio data as bytes
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            # Convert to AudioSegment in memory
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
            
            # Export to WAV format in memory
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format="wav")
            wav_data = wav_buffer.getvalue()
            
            # Play the audio using pygame
            play_audio_from_memory(wav_data)
            
        except Exception as e:
            print(f"Error during text-to-speech: {e}")
        finally:
            # Resume listening after a short delay
            time.sleep(0.5)  # Wait for audio to fully stop
            with audio_lock:
                listening_active = True

    def speak_text_sync(text):
        asyncio.run(speak_text(text))

    def query_chroma_db(question_text, top_k=1):
        if not question_text.strip():
            return ["Sorry, I didn't catch that. Could you please repeat your question?"]
        
        # Simple check for garbled speech recognition
        garbled_indicators = ["murder", "oh i see", "that is", "of and that"]
        question_lower = question_text.lower()
        for indicator in garbled_indicators:
            if indicator in question_lower:
                return ["I'm having trouble understanding. Could you please repeat your question more clearly?"]
        
        query_emb = embedder.encode([question_text])
        results = collection.query(
            query_embeddings=query_emb.tolist(),
            n_results=top_k
        )
        
        answers = []
        for i in range(len(results["metadatas"][0])):
            answer = results["metadatas"][0][i].get("answer", "No answer found.")
            answers.append(answer)
        return answers

    # Play greeting message
    print('\n--- Voice Assistant Ready ---')
    print('Speak into the microphone, press Ctrl+C to stop.\n')
    print('Note: The assistant will pause listening while speaking to avoid feedback.\n')
    
    # Speak the greeting
    print("Playing greeting message...")
    speak_text_sync(GREETING_MESSAGE)

    try:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=8000,
            device=None,
            dtype='int16',
            channels=1,
            callback=audio_callback
        ):
            recognizer = vosk.KaldiRecognizer(vosk_model, SAMPLE_RATE)

            while True:
                data = q_audio.get()
                if recognizer.AcceptWaveform(data):
                    result_json = json.loads(recognizer.Result())
                    text = result_json.get('text', '').strip()
                    if text:
                        print(f"\nYou said: {text}")
                        answers = query_chroma_db(text, top_k=1)
                        reply = answers[0]
                        print(f"Answer: {reply}")
                        speak_text_sync(reply)
                else:
                    partial_json = json.loads(recognizer.PartialResult())
                    partial = partial_json.get('partial', '')
                    if partial:
                        print(f"Listening: {partial}", end='\r')

    except KeyboardInterrupt:
        print('\nVoice assistant stopped by user.')
    except Exception as e:
        print(f"Error: {e}")


def main():
    client = chromadb.Client(
        chromadb.config.Settings(
            persist_directory=PERSIST_DIRECTORY
        )
    )
    embedder = SentenceTransformer('all-MiniLM-L6-v2')

    collection = get_existing_collection(client)
    if collection is None:
        collection = upload_excel_to_chroma(client, embedder)

    run_voice_assistant(collection, embedder)


if __name__ == "__main__":
    main()
