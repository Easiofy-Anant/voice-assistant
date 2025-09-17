import os
import json
import base64
import asyncio
import uvicorn
import openai
import tempfile
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydub import AudioSegment
import io
import edge_tts
import requests
from typing import Optional, Dict, List
import time
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set OpenAI API key - MAKE SURE THIS IS SET!
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.error("OPENAI_API_KEY environment variable not set! Voice features will not work.")
else:
    openai.api_key = openai_api_key

# Configuration - Optimized for speed
USE_WHISPER = True
OPENAI_MODEL = "gpt-3.5-turbo"
MAX_RECORDING_TIME = 10  # Seconds
RESPONSE_TIMEOUT = 15  # Seconds

# Initialize FastAPI
app = FastAPI(
    title="BigShip Voice Assistant - Optimized",
    description="Fast voice assistant with auto voice detection",
    version="7.0.0"
)

# Global state
conversation_state = {
    "is_listening": False,
    "is_processing": False,
    "is_speaking": False,
    "current_websocket": None,
    "performance_stats": {
        "transcription_time": 0,
        "response_time": 0,
        "tts_time": 0,
        "total_time": 0
    }
}

# Performance monitoring
class PerformanceMonitor:
    def __init__(self):
        self.start_time = None
        self.metrics = {}
        
    def start(self):
        self.start_time = time.time()
        self.metrics = {
            "transcription_time": 0,
            "response_time": 0,
            "tts_time": 0
        }
        
    def record(self, stage):
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.metrics[stage] = elapsed
            self.start_time = time.time()
            
    def get_metrics(self):
        total = sum(self.metrics.values())
        return {**self.metrics, "total_time": total}

performance_monitor = PerformanceMonitor()

async def transcribe_audio_openai(audio_data: bytes) -> str:
    """Optimized transcription with better error handling"""
    try:
        logger.info("Starting transcription...")
        performance_monitor.start()
        
        # Convert webm to wav with optimal settings
        audio = AudioSegment.from_file(io.BytesIO(audio_data), format="webm")
        
        # Optimize audio for Whisper
        audio = audio.set_frame_rate(16000).set_channels(1)
        
        # Don't trim silence as it might remove valid speech
        # Just normalize volume
        audio = audio.normalize()
        
        if len(audio) < 300:  # Less than 0.3 seconds
            logger.warning("Audio too short")
            return ""
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio.export(tmp.name, format="wav")
            tmp_path = tmp.name
        
        try:
            # Check if API key is configured
            if not openai_api_key:
                logger.error("OpenAI API key not configured")
                return "[ERROR: API key not configured]"
                
            # Transcribe with Whisper
            client = openai.OpenAI(api_key=openai_api_key)
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                    language="en"
                )
            
            performance_monitor.record("transcription_time")
            logger.info(f"Transcription completed: {transcript.strip()}")
            
            return transcript.strip()
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return f"[Transcription Error: {str(e)}]"

async def get_openai_response(user_input: str) -> str:
    """Optimized OpenAI response with faster model"""
    try:
        logger.info("Getting AI response...")
        
        if not user_input.strip() or user_input.startswith("[ERROR"):
            return "I didn't catch that. Could you please repeat?"
        
        # Check if API key is configured
        if not openai_api_key:
            return "[ERROR: OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable.]"
        
        # Shorter, more focused system prompt
        system_prompt = """You are BigShip's helpful voice assistant. Give short, clear answers (1-2 sentences max) about shipping and logistics. Key info: BigShip offers 40% savings, covers 25,000+ pin codes, partners with major couriers, provides real-time tracking."""
        
        # Get response from OpenAI
        client = openai.OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=60,  # Shorter responses
            temperature=0.3,
            timeout=10  # 10 second timeout
        )
        
        performance_monitor.record("response_time")
        
        result = response.choices[0].message.content.strip()
        logger.info(f"AI response: {result}")
        return result
    
    except Exception as e:
        logger.error(f"OpenAI response error: {e}")
        return f"I'm having trouble connecting right now. Error: {str(e)}"

async def text_to_speech(text: str) -> str:
    """Optimized TTS with faster voice and shorter text"""
    try:
        logger.info("Generating speech...")
        
        # Limit text length
        if len(text) > 150:
            text = text[:147] + "..."
        
        # Use faster voice settings
        communicate = edge_tts.Communicate(
            text, 
            "en-US-JennyNeural",  # Faster US voice
            rate="+10%",  # Slightly faster speech
            pitch="+0Hz"
        )
        
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        
        performance_monitor.record("tts_time")
        logger.info("TTS completed successfully")
        
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return ""

async def process_audio(audio_data: bytes):
    """Optimized processing pipeline"""
    total_start_time = time.time()
    
    try:
        # Step 1: Transcribe
        transcription = await asyncio.wait_for(
            transcribe_audio_openai(audio_data), 
            timeout=15
        )
        
        if not transcription or transcription.startswith("[ERROR"):
            return {
                "error": "Could not understand audio. Please speak clearly and try again.",
                "processing_time": time.time() - total_start_time
            }
        
        logger.info(f"Transcription: {transcription}")
        
        # Step 2: Get AI response
        response = await asyncio.wait_for(
            get_openai_response(transcription), 
            timeout=15
        )
        
        # Step 3: Generate speech (run in parallel with response if needed)
        audio_base64 = await asyncio.wait_for(
            text_to_speech(response), 
            timeout=10
        )
        
        processing_time = time.time() - total_start_time
        metrics = performance_monitor.get_metrics()
        logger.info(f"Total processing time: {processing_time:.2f}s")
        
        return {
            "transcription": transcription,
            "response": response,
            "audio_base64": audio_base64,
            "processing_time": processing_time,
            "metrics": metrics
        }
        
    except asyncio.TimeoutError:
        logger.error("Processing timeout")
        return {
            "error": "Processing took too long. Please try again.",
            "processing_time": time.time() - total_start_time
        }
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return {
            "error": f"An error occurred: {str(e)}",
            "processing_time": time.time() - total_start_time
        }

# WebSocket endpoint with better error handling
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conversation_state["current_websocket"] = websocket
    logger.info("WebSocket connected")
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "audio_data":
                conversation_state["is_processing"] = True
                await websocket.send_json({
                    "type": "state_update", 
                    "is_processing": True
                })
                
                try:
                    # Process audio
                    audio_bytes = base64.b64decode(data["audio"])
                    result = await process_audio(audio_bytes)
                    
                    if "error" in result:
                        await websocket.send_json({
                            "type": "error",
                            "message": result["error"],
                            "processing_time": result["processing_time"]
                        })
                    else:
                        await websocket.send_json({
                            "type": "response",
                            "transcription": result["transcription"],
                            "response": result["response"],
                            "audio_base64": result["audio_base64"],
                            "processing_time": result["processing_time"],
                            "metrics": result.get("metrics", {})
                        })
                        
                except Exception as e:
                    logger.error(f"Audio processing error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Failed to process audio: {str(e)}"
                    })
                
                finally:
                    conversation_state["is_processing"] = False
                    await websocket.send_json({
                        "type": "state_update", 
                        "is_processing": False
                    })
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        conversation_state["current_websocket"] = None
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

# API endpoint to check configuration
@app.get("/api/status")
async def get_status():
    """Check if the API is configured correctly"""
    api_configured = bool(openai_api_key)
    return {
        "openai_configured": api_configured,
        "model": OPENAI_MODEL,
        "use_whisper": USE_WHISPER,
        "performance_metrics": conversation_state["performance_stats"]
    }

# API endpoint to test audio processing
@app.post("/api/test-audio")
async def test_audio_processing():
    """Test endpoint to verify audio processing works"""
    # Create a short silent audio segment for testing
    audio = AudioSegment.silent(duration=1000)  # 1 second of silence
    buffer = io.BytesIO()
    audio.export(buffer, format="wav")
    audio_data = buffer.getvalue()
    
    result = await process_audio(audio_data)
    return result

# Frontend HTML with improved debugging
@app.get("/", response_class=HTMLResponse)
async def get_homepage():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BigShip Voice Assistant - Debug Mode</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            padding: 20px;
        }

        .container {
            text-align: center;
            max-width: 800px;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        .logo {
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .subtitle {
            font-size: 1.2rem;
            margin-bottom: 2rem;
            opacity: 0.9;
        }

        .debug-panel {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
            text-align: left;
            max-height: 200px;
            overflow-y: auto;
        }

        .debug-entry {
            margin: 5px 0;
            font-family: monospace;
            font-size: 0.9rem;
        }

        .debug-error {
            color: #ff6b6b;
        }

        .debug-warning {
            color: #ffa726;
        }

        .debug-info {
            color: #4ecdc4;
        }

        .mic-container {
            position: relative;
            margin: 2rem 0;
        }

        .mic-button {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            color: white;
            font-size: 3rem;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto;
        }

        .mic-button:hover {
            transform: scale(1.05);
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.4);
        }

        .mic-button.recording {
            background: linear-gradient(45deg, #ff4757, #ff3742);
            animation: pulse 1.5s infinite;
        }

        .mic-button.processing {
            background: linear-gradient(45deg, #ffa726, #ff9800);
            animation: spin 1s linear infinite;
        }

        .mic-button.listening {
            background: linear-gradient(45deg, #2ecc71, #27ae60);
            animation: listening 2s ease-in-out infinite;
        }

        @keyframes pulse {
            0% { box-shadow: 0 8px 25px rgba(255, 71, 87, 0.3); }
            50% { box-shadow: 0 8px 25px rgba(255, 71, 87, 0.8), 0 0 0 15px rgba(255, 71, 87, 0.2); }
            100% { box-shadow: 0 8px 25px rgba(255, 71, 87, 0.3); }
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        @keyframes listening {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.1); opacity: 0.8; }
        }

        .status {
            font-size: 1.1rem;
            margin: 1rem 0;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .volume-indicator {
            width: 200px;
            height: 10px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 5px;
            margin: 1rem auto;
            overflow: hidden;
        }

        .volume-bar {
            height: 100%;
            background: linear-gradient(45deg, #2ecc71, #27ae60);
            width: 0%;
            transition: width 0.1s ease;
        }

        .conversation {
            max-width: 500px;
            margin: 2rem auto 0;
            text-align: left;
            max-height: 300px;
            overflow-y: auto;
        }

        .message {
            margin: 1rem 0;
            padding: 1rem;
            border-radius: 15px;
            max-width: 80%;
            word-wrap: break-word;
        }

        .user-message {
            background: rgba(255, 255, 255, 0.2);
            margin-left: auto;
            text-align: right;
        }

        .assistant-message {
            background: rgba(78, 205, 196, 0.3);
            margin-right: auto;
        }

        .error {
            color: #ff6b6b;
            font-weight: bold;
            text-align: center;
        }

        .processing-time {
            font-size: 0.8rem;
            opacity: 0.7;
            margin-top: 0.5rem;
        }

        .metrics {
            font-size: 0.7rem;
            opacity: 0.6;
            margin-top: 0.3rem;
        }

        .controls {
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin-top: 2rem;
            flex-wrap: wrap;
        }

        .control-button {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(5px);
            font-size: 0.9rem;
        }

        .control-button:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }

        .control-button.active {
            background: rgba(46, 204, 113, 0.5);
        }

        .config-status {
            padding: 10px;
            border-radius: 8px;
            margin: 10px 0;
            text-align: center;
        }

        .config-ok {
            background: rgba(46, 204, 113, 0.3);
        }

        .config-error {
            background: rgba(255, 107, 107, 0.3);
        }

        @media (max-width: 768px) {
            .container {
                margin: 1rem;
                padding: 1.5rem;
            }
            
            .logo {
                font-size: 2.5rem;
            }
            
            .mic-button {
                width: 100px;
                height: 100px;
                font-size: 2.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🚢 BigShip</div>
        <div class="subtitle">Voice Assistant - Debug Mode</div>
        
        <div id="configStatus" class="config-status config-error">
            Checking OpenAI API configuration...
        </div>
        
        <div class="debug-panel" id="debugPanel">
            <div class="debug-entry debug-info">System initialized. Click to start.</div>
        </div>
        
        <div class="mic-container">
            <button class="mic-button" id="micButton">🎤</button>
        </div>
        
        <div class="volume-indicator">
            <div class="volume-bar" id="volumeBar"></div>
        </div>
        
        <div class="status" id="status">Click to start listening</div>
        
        <div class="controls">
            <button class="control-button" id="autoModeButton">Auto Mode: OFF</button>
            <button class="control-button" id="clearButton">Clear Chat</button>
            <button class="control-button" id="testButton">Test Connection</button>
            <button class="control-button" id="debugButton">Debug Info</button>
        </div>
        
        <div class="conversation" id="conversation"></div>
    </div>

    <script>
        class VoiceAssistant {
            constructor() {
                this.ws = null;
                this.mediaRecorder = null;
                this.audioChunks = [];
                this.isRecording = false;
                this.isProcessing = false;
                this.autoMode = false;
                this.audioContext = null;
                this.analyser = null;
                this.microphone = null;
                this.volumeThreshold = 25; // Lowered for better sensitivity
                this.silenceTimeout = null;
                this.silenceDelay = 2000; // 2 seconds of silence before stopping
                this.debugMode = true;
                
                this.micButton = document.getElementById('micButton');
                this.status = document.getElementById('status');
                this.conversation = document.getElementById('conversation');
                this.clearButton = document.getElementById('clearButton');
                this.testButton = document.getElementById('testButton');
                this.autoModeButton = document.getElementById('autoModeButton');
                this.debugButton = document.getElementById('debugButton');
                this.volumeBar = document.getElementById('volumeBar');
                this.debugPanel = document.getElementById('debugPanel');
                this.configStatus = document.getElementById('configStatus');
                
                this.checkConfiguration();
                this.initializeWebSocket();
                this.setupEventListeners();
            }
            
            async checkConfiguration() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    
                    if (data.openai_configured) {
                        this.configStatus.textContent = '✅ OpenAI API is configured correctly';
                        this.configStatus.className = 'config-status config-ok';
                        this.addDebugEntry('OpenAI API configured correctly', 'info');
                    } else {
                        this.configStatus.textContent = '❌ OpenAI API key not configured. Set OPENAI_API_KEY environment variable.';
                        this.configStatus.className = 'config-status config-error';
                        this.addDebugEntry('OpenAI API not configured - voice features will not work', 'error');
                    }
                } catch (error) {
                    this.configStatus.textContent = '❌ Could not check server configuration';
                    this.configStatus.className = 'config-status config-error';
                    this.addDebugEntry('Failed to check server configuration: ' + error, 'error');
                }
            }
            
            addDebugEntry(message, type = 'info') {
                if (!this.debugMode) return;
                
                const entry = document.createElement('div');
                entry.className = `debug-entry debug-${type}`;
                entry.textContent = new Date().toLocaleTimeString() + ' - ' + message;
                this.debugPanel.appendChild(entry);
                this.debugPanel.scrollTop = this.debugPanel.scrollHeight;
            }
            
            initializeWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    this.addDebugEntry('WebSocket connected to server', 'info');
                    this.updateStatus('✅ Connected! Click to start or enable Auto Mode');
                };
                
                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                };
                
                this.ws.onclose = () => {
                    this.addDebugEntry('WebSocket disconnected, attempting to reconnect...', 'warning');
                    this.updateStatus('❌ Disconnected. Reconnecting...');
                    setTimeout(() => this.initializeWebSocket(), 3000);
                };
                
                this.ws.onerror = (error) => {
                    this.addDebugEntry('WebSocket error: ' + error, 'error');
                    this.updateStatus('Connection error');
                };
            }
            
            setupEventListeners() {
                this.micButton.addEventListener('click', () => {
                    if (this.autoMode) {
                        this.toggleAutoMode();
                    } else {
                        if (this.isRecording) {
                            this.stopRecording();
                        } else if (!this.isProcessing) {
                            this.startRecording();
                        }
                    }
                });
                
                this.autoModeButton.addEventListener('click', () => {
                    this.toggleAutoMode();
                });
                
                this.clearButton.addEventListener('click', () => {
                    this.conversation.innerHTML = '';
                    this.debugPanel.innerHTML = '';
                    this.addDebugEntry('Cleared conversation and debug logs', 'info');
                });
                
                this.testButton.addEventListener('click', () => {
                    this.testConnection();
                });
                
                this.debugButton.addEventListener('click', () => {
                    this.debugMode = !this.debugMode;
                    this.debugButton.textContent = this.debugMode ? 'Debug: ON' : 'Debug: OFF';
                    this.debugButton.classList.toggle('active', this.debugMode);
                    this.addDebugEntry('Debug mode ' + (this.debugMode ? 'enabled' : 'disabled'), 'info');
                });
            }
            
            async toggleAutoMode() {
                this.autoMode = !this.autoMode;
                
                if (this.autoMode) {
                    this.autoModeButton.textContent = 'Auto Mode: ON';
                    this.autoModeButton.classList.add('active');
                    this.addDebugEntry('Auto mode enabled', 'info');
                    await this.startAutoListening();
                } else {
                    this.autoModeButton.textContent = 'Auto Mode: OFF';
                    this.autoModeButton.classList.remove('active');
                    this.addDebugEntry('Auto mode disabled', 'info');
                    this.stopAutoListening();
                }
            }
            
            async startAutoListening() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ 
                        audio: {
                            sampleRate: 16000,
                            channelCount: 1,
                            volume: 1.0,
                            echoCancellation: true,
                            noiseSuppression: true
                        } 
                    });
                    
                    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    this.analyser = this.audioContext.createAnalyser();
                    this.microphone = this.audioContext.createMediaStreamSource(stream);
                    
                    this.analyser.fftSize = 256;
                    this.microphone.connect(this.analyser);
                    
                    this.updateUI('listening');
                    this.updateStatus('🎧 Auto listening... Speak naturally');
                    this.addDebugEntry('Auto listening started', 'info');
                    
                    this.monitorAudio();
                    
                } catch (error) {
                    console.error('Error starting auto listening:', error);
                    this.addDebugEntry('Microphone access denied: ' + error, 'error');
                    this.updateStatus('❌ Microphone access denied');
                    this.autoMode = false;
                    this.autoModeButton.textContent = 'Auto Mode: OFF';
                    this.autoModeButton.classList.remove('active');
                }
            }
            
            monitorAudio() {
                if (!this.autoMode) return;
                
                const bufferLength = this.analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);
                
                const checkAudio = () => {
                    if (!this.autoMode) return;
                    
                    this.analyser.getByteFrequencyData(dataArray);
                    
                    // Calculate average volume
                    const average = dataArray.reduce((a, b) => a + b) / bufferLength;
                    
                    // Update volume indicator
                    this.volumeBar.style.width = `${Math.min(average * 2, 100)}%`;
                    
                    // Voice activity detection
                    if (average > this.volumeThreshold && !this.isRecording && !this.isProcessing) {
                        this.addDebugEntry(`Voice detected (volume: ${average.toFixed(1)}), starting recording`, 'info');
                        this.startRecording(true); // Pass true for auto mode
                    } else if (this.isRecording && average < this.volumeThreshold / 2) {
                        // Start silence timer
                        if (!this.silenceTimeout) {
                            this.silenceTimeout = setTimeout(() => {
                                if (this.isRecording) {
                                    this.addDebugEntry('Silence detected, stopping recording', 'info');
                                    this.stopRecording();
                                }
                                this.silenceTimeout = null;
                            }, this.silenceDelay);
                        }
                    } else if (this.isRecording && average > this.volumeThreshold / 2) {
                        // Cancel silence timer if voice detected again
                        if (this.silenceTimeout) {
                            clearTimeout(this.silenceTimeout);
                            this.silenceTimeout = null;
                        }
                    }
                    
                    requestAnimationFrame(checkAudio);
                };
                
                checkAudio();
            }
            
            stopAutoListening() {
                if (this.audioContext) {
                    this.audioContext.close();
                    this.audioContext = null;
                }
                if (this.microphone) {
                    this.microphone.disconnect();
                    this.microphone = null;
                }
                if (this.analyser) {
                    this.analyser = null;
                }
                if (this.silenceTimeout) {
                    clearTimeout(this.silenceTimeout);
                    this.silenceTimeout = null;
                }
                if (this.isRecording) {
                    this.stopRecording();
                }
                this.updateUI('idle');
                this.updateStatus('Click to start or enable Auto Mode');
                this.volumeBar.style.width = '0%';
                this.addDebugEntry('Auto listening stopped', 'info');
            }
            
            async startRecording(autoMode = false) {
                try {
                    let stream;
                    
                    if (autoMode && this.microphone) {
                        // Use existing stream for auto mode
                        stream = this.microphone.mediaStream;
                    } else {
                        // Create new stream for manual mode
                        stream = await navigator.mediaDevices.getUserMedia({ 
                            audio: {
                                sampleRate: 16000,
                                channelCount: 1,
                                volume: 1.0,
                                echoCancellation: true,
                                noiseSuppression: true
                            } 
                        });
                    }
                    
                    this.mediaRecorder = new MediaRecorder(stream, {
                        mimeType: 'audio/webm;codecs=opus'
                    });
                    
                    this.audioChunks = [];
                    this.isRecording = true;
                    
                    this.mediaRecorder.ondataavailable = (event) => {
                        if (event.data.size > 0) {
                            this.audioChunks.push(event.data);
                        }
                    };
                    
                    this.mediaRecorder.onstop = () => {
                        this.processRecording();
                    };
                    
                    this.mediaRecorder.start();
                    
                    if (!autoMode) {
                        this.updateUI('recording');
                        this.updateStatus('🎤 Recording... Click to stop or wait for silence');
                        this.addDebugEntry('Manual recording started', 'info');
                    } else {
                        this.updateUI('recording');
                        this.updateStatus('🎤 Recording detected speech...');
                    }
                    
                } catch (error) {
                    console.error('Error starting recording:', error);
                    this.addDebugEntry('Microphone access denied: ' + error, 'error');
                    this.updateStatus('❌ Microphone access denied');
                }
            }
            
            stopRecording() {
                if (this.mediaRecorder && this.isRecording) {
                    this.mediaRecorder.stop();
                    if (!this.autoMode) {
                        // Only stop tracks in manual mode
                        this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
                    }
                    this.isRecording = false;
                    this.updateUI('processing');
                    this.updateStatus('⏳ Processing...');
                    this.addDebugEntry('Recording stopped, processing audio', 'info');
                }
            }
            
            async processRecording() {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                const arrayBuffer = await audioBlob.arrayBuffer();
                const base64Audio = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
                
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.addDebugEntry('Sending audio to server for processing', 'info');
                    this.ws.send(JSON.stringify({
                        type: 'audio_data',
                        audio: base64Audio
                    }));
                } else {
                    this.addDebugEntry('WebSocket not connected, cannot send audio', 'error');
                    this.updateStatus('❌ Connection error. Please refresh.');
                    this.updateUI('idle');
                }
            }
            
            handleWebSocketMessage(data) {
                switch (data.type) {
                    case 'response':
                        this.handleResponse(data);
                        break;
                    case 'error':
                        this.handleError(data.message, data.processing_time);
                        break;
                    case 'state_update':
                        this.isProcessing = data.is_processing;
                        break;
                }
            }
            
            handleResponse(data) {
                // Add user message
                this.addMessage(data.transcription, 'user');
                
                // Add assistant response
                this.addMessage(data.response, 'assistant', data.processing_time, data.metrics);
                
                // Play audio response
                if (data.audio_base64) {
                    this.playAudio(data.audio_base64);
                }
                
                this.addDebugEntry(`Processing completed in ${data.processing_time.toFixed(2)}s`, 'info');
                
                if (this.autoMode) {
                    this.updateUI('listening');
                    this.updateStatus('🎧 Listening for next question...');
                } else {
                    this.updateUI('idle');
                    this.updateStatus('✅ Click to ask another question');
                }
            }
            
            handleError(message, processingTime = null) {
                this.addDebugEntry('Error: ' + message, 'error');
                this.addMessage(message, 'error', processingTime);
                
                if (this.autoMode) {
                    this.updateUI('listening');
                    this.updateStatus('🎧 Error occurred. Listening again...');
                } else {
                    this.updateUI('idle');
                    this.updateStatus('❌ Error occurred. Please try again.');
                }
            }
            
            addMessage(text, type, processingTime = null, metrics = null) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${type}-message`;
                messageDiv.textContent = text;
                
                if (processingTime) {
                    const timeDiv = document.createElement('div');
                    timeDiv.className = 'processing-time';
                    timeDiv.textContent = `⏱️ ${processingTime.toFixed(1)}s`;
                    messageDiv.appendChild(timeDiv);
                }
                
                if (metrics) {
                    const metricsDiv = document.createElement('div');
                    metricsDiv.className = 'metrics';
                    metricsDiv.textContent = `Transcription: ${metrics.transcription_time?.toFixed(1) || 0}s, Response: ${metrics.response_time?.toFixed(1) || 0}s, TTS: ${metrics.tts_time?.toFixed(1) || 0}s`;
                    messageDiv.appendChild(metricsDiv);
                }
                
                this.conversation.appendChild(messageDiv);
                this.conversation.scrollTop = this.conversation.scrollHeight;
            }
            
            playAudio(base64Audio) {
                try {
                    const audio = new Audio(`data:audio/mpeg;base64,${base64Audio}`);
                    audio.play().catch(error => {
                        this.addDebugEntry('Audio playback error: ' + error, 'error');
                    });
                } catch (error) {
                    this.addDebugEntry('Audio creation error: ' + error, 'error');
                }
            }
            
            updateUI(state) {
                this.micButton.className = `mic-button ${state}`;
                
                switch (state) {
                    case 'recording':
                        this.micButton.innerHTML = '⏹️';
                        break;
                    case 'processing':
                        this.micButton.innerHTML = '⏳';
                        break;
                    case 'listening':
                        this.micButton.innerHTML = '🎧';
                        break;
                    default:
                        this.micButton.innerHTML = '🎤';
                }
            }
            
            updateStatus(message) {
                this.status.innerHTML = message;
            }
            
            testConnection() {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.addDebugEntry('Connection test: WebSocket is connected', 'info');
                    this.updateStatus('✅ Connection is working perfectly!');
                    setTimeout(() => {
                        if (this.autoMode) {
                            this.updateStatus('🎧 Auto listening mode active');
                        } else {
                            this.updateStatus('Click to start or enable Auto Mode');
                        }
                    }, 2000);
                } else {
                    this.addDebugEntry('Connection test: WebSocket is not connected', 'error');
                    this.updateStatus('❌ Connection failed - refresh page');
                }
            }
        }
        
        // Initialize the voice assistant when page loads
        document.addEventListener('DOMContentLoaded', () => {
            window.assistant = new VoiceAssistant();
        });
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page is hidden, pause auto mode
                console.log('Page hidden, pausing auto mode');
            } else {
                // Page is visible again
                console.log('Page visible again');
            }
        });
    </script>
</body>
</html>'''

if __name__ == "__main__":
    print("🚀 BigShip Voice Assistant - Debug Edition")
    print("📱 Starting on http://127.0.0.1:8000")
    print("🔧 Debug Features:")
    print("   • API configuration check")
    print("   • Detailed error messages")
    print("   • Performance metrics")
    print("   • Real-time debug logging")
    print("   • Volume threshold adjustments")
    print("\n🎯 Troubleshooting Tips:")
    print("   1. Check if OPENAI_API_KEY is set correctly")
    print("   2. Test microphone permissions in your browser")
    print("   3. Check the debug panel for error messages")
    print("   4. Adjust volume threshold if needed")
    print("   5. Try both manual and auto modes")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)
