# Bigship AI Voice Assistant

A sophisticated AI-powered voice assistant designed to provide information about Bigship's courier and shipping services. The assistant uses natural language processing, speech recognition, and text-to-speech to create an interactive conversational experience.

## 🚀 Features

### Core Functionality
- **Real-time Speech Recognition** - Converts spoken questions to text using Vosk
- **Semantic Search** - Finds relevant answers using sentence transformers and ChromaDB
- **Text-to-Speech** - Converts answers to natural speech using Edge TTS
- **Voice Feedback Prevention** - Prevents the assistant from hearing its own output
- **Persistent Knowledge Base** - Stores Q&A data in ChromaDB for fast retrieval
- **Greeting System** - Welcomes users with a professional introduction

### Smart Question Handling
- **Garbled Speech Detection** - Identifies unclear speech and asks for clarification
- **Semantic Matching** - Finds the most relevant answer even with paraphrased questions
- **Multi-sheet Data Support** - Processes Excel files with multiple sheets
- **Automatic Data Persistence** - No need to reload data on subsequent runs

## 🛠️ Technology Stack

### Speech Processing
- **Vosk** - Offline speech recognition engine
- **SoundDevice** - Real-time audio input/output handling
- **Pygame** - Audio playback for cross-platform compatibility

### Natural Language Processing
- **Sentence Transformers** - Semantic text embeddings using 'all-MiniLM-L6-v2'
- **ChromaDB** - Vector database for semantic search and storage
- **Edge TTS** - Microsoft's text-to-speech service for natural voice synthesis

### Data Processing
- **Pandas** - Excel file processing and data manipulation
- **OpenPyXL** - Excel file reading and parsing
- **Pydub** - Audio format conversion and processing

### Audio Processing
- **Pygame Mixer** - Cross-platform audio playback
- **IO BytesIO** - In-memory audio processing to avoid file permission issues

### Development & Environment
- **Python 3.10** - Core programming language
- **Virtual Environment** - Isolated dependency management
- **Windows 10/11** - Primary development platform

## 📁 Project Structure

```
310/
├── app.py                          # Main application file
├── README.md                       # Project documentation
├── requirements.txt                # Python dependencies
├── Merged_File_with_Sheets.xlsx   # Knowledge base data
├── chroma_db/                      # Persistent vector database
├── vosk-model-small-en-us-0.15/   # Speech recognition model
└── venv_310/                      # Python virtual environment
```

## ✅ Current Setup Status

### Environment Details
- **Operating System**: Windows 10/11
- **IDE**: Visual Studio Code
- **Python Version**: 3.10
- **Virtual Environment**: venv_310
- **Project Location**: `C:\Users\mysel\OneDrive\Pictures\310\`

### ✅ Components Successfully Installed

#### Core Dependencies
- ✅ **pandas** - Excel data processing
- ✅ **sounddevice** - Real-time audio input/output
- ✅ **vosk** - Offline speech recognition
- ✅ **chromadb** - Vector database for semantic search
- ✅ **sentence-transformers** - Text embeddings
- ✅ **edge-tts** - Microsoft text-to-speech
- ✅ **pydub** - Audio format conversion
- ✅ **pygame** - Cross-platform audio playback
- ✅ **openpyxl** - Excel file reading

#### Models & Data
- ✅ **Vosk Model** - `vosk-model-small-en-us-0.15/` (speech recognition)
- ✅ **Knowledge Base** - `Merged_File_with_Sheets.xlsx` (94 Q&A pairs)
- ✅ **ChromaDB** - `chroma_db/` (persistent vector database)

### 🎯 Current Functionality

#### Working Features
- ✅ **Real-time Speech Recognition** - Converts voice to text
- ✅ **Semantic Search** - Finds relevant answers from knowledge base
- ✅ **Text-to-Speech** - Converts answers to natural speech
- ✅ **Voice Feedback Prevention** - Prevents hearing own output
- ✅ **Persistent Knowledge Base** - No reloading needed
- ✅ **Greeting System** - Professional welcome message
- ✅ **Garbled Speech Detection** - Handles unclear input gracefully

#### Tested Capabilities
- ✅ **Basic Questions** - "What is Bigship?", "How does Bigship work?"
- ✅ **Vendor Registration** - "How do I become a vendor?"
- ✅ **Service Inquiries** - Various shipping and service questions
- ✅ **Error Handling** - Graceful handling of unclear speech

### 📊 Performance Metrics

#### Data Processing
- **Knowledge Base**: 94 Q&A pairs across 4 Excel sheets
- **Processing Time**: ~6 seconds for initial data loading
- **Memory Usage**: Efficient in-memory audio processing
- **Response Time**: Near real-time voice interaction

#### Accuracy
- **Speech Recognition**: Good for clear speech
- **Answer Relevance**: High semantic matching accuracy
- **Voice Quality**: Natural Edge TTS synthesis
- **Error Recovery**: Graceful handling of unclear input

## 🚀 Complete Setup Guide

### Prerequisites
- **Python 3.10 or higher** - Download from [python.org](https://python.org)
- **Windows 10/11** (tested platform)
- **Microphone and speakers** - For voice interaction
- **Internet connection** - Required for Edge TTS and initial setup
- **Git** (optional) - For cloning the repository

### Step 1: Project Setup

1. **Create project directory**
   ```bash
   mkdir bigship-voice-assistant
   cd bigship-voice-assistant
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv_310
   ```

3. **Activate virtual environment**
   ```bash
   # Windows
   venv_310\Scripts\activate
   
   # Linux/Mac
   source venv_310/bin/activate
   ```

### Step 2: Install Dependencies

1. **Install from requirements.txt**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify installation**
   ```bash
   python -c "import pandas, sounddevice, vosk, chromadb, sentence_transformers, edge_tts, pydub, pygame, openpyxl; print('All dependencies installed successfully!')"
   ```

### Step 3: Download Vosk Speech Recognition Model

1. **Download the model**
   - Visit: https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   - Or use direct link: https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

2. **Extract the model**
   ```bash
   # Download using curl (if available)
   curl -L -o vosk-model-small-en-us-0.15.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   
   # Extract the zip file
   # Windows: Right-click → Extract All
   # Or use: tar -xf vosk-model-small-en-us-0.15.zip
   ```

3. **Verify model structure**
   ```
   vosk-model-small-en-us-0.15/
   ├── am/
   ├── conf/
   ├── graph/
   ├── ivector/
   └── README
   ```

### Step 4: Prepare Knowledge Base Data

1. **Create Excel file structure**
   - Create `Merged_File_with_Sheets.xlsx`
   - Add multiple sheets: "BigShip Overview", "Onboarding & Registration", "Services & Shipping Options", "Pricing, Payments & COD"
   - Format: Column A = Questions, Column C = Answers (skip Column B)

2. **Sample Excel structure:**
   ```
   Sheet: BigShip Overview
   A1: What is Bigship?
   C1: Bigship is a courier aggregator company...
   
   A2: How does Bigship work?
   C2: Bigship operates as a technology-enabled platform...
   ```

### Step 5: Configure the Application

1. **Update file paths in app.py**
   ```python
   # Update these paths to match your setup
   EXCEL_PATH = r"C:\path\to\your\Merged_File_with_Sheets.xlsx"
   PERSIST_DIRECTORY = r"C:\path\to\your\chroma_db"
   VOSK_MODEL_PATH = r"C:\path\to\your\vosk-model-small-en-us-0.15"
   ```

2. **Verify configuration**
   - Ensure all paths exist and are accessible
   - Check that Excel file has proper Q&A format
   - Confirm Vosk model directory structure is correct

### Step 6: ChromaDB Setup

1. **ChromaDB will be created automatically**
   - The application creates the database on first run
   - No manual setup required
   - Data persists between sessions

2. **Database location**
   - Default: `./chroma_db/` in project directory
   - Can be customized via `PERSIST_DIRECTORY` in app.py

3. **First run behavior**
   - ChromaDB collection created automatically
   - Excel data loaded and embedded
   - Subsequent runs use existing database

### Step 7: Test the Setup

1. **Run the application**
   ```bash
   python app.py
   ```

2. **Expected output**
   ```
   pygame 2.6.1 (SDL 2.28.4, Python 3.10.0)
   Hello from the pygame community. https://www.pygame.org/contribute.html
   Collection 'qna_collection' does not exist.
   Uploading Excel data to ChromaDB...
   Created collection 'qna_collection'
   Processing sheet: BigShip Overview
   ...
   Uploaded 94 Q&A pairs successfully.
   
   --- Voice Assistant Ready ---
   Speak into the microphone, press Ctrl+C to stop.
   
   Note: The assistant will pause listening while speaking to avoid feedback.
   
   Playing greeting message...
   ```

3. **Test voice interaction**
   - Wait for greeting message
   - Speak clearly: "What is Bigship?"
   - Listen for response
   - Continue conversation

## 🎯 Usage

### Starting the Assistant
1. Run the application: `python app.py`
2. Wait for the greeting message
3. Speak your question clearly
4. Listen to the response
5. Continue the conversation

### Example Questions
- "What is Bigship?"
- "How does Bigship work?"
- "How do I become a vendor?"
- "What are the shipping rates?"
- "How do I track my shipment?"

### Voice Commands
- **Speak clearly** - For best recognition results
- **Wait for response** - Assistant pauses listening while speaking
- **Ctrl+C** - Stop the assistant

## 🔧 Technical Architecture

### Data Flow
1. **Voice Input** → Vosk Speech Recognition → Text
2. **Text Query** → Sentence Transformers → Embeddings
3. **Embeddings** → ChromaDB → Semantic Search
4. **Best Match** → Answer Selection
5. **Answer** → Edge TTS → Audio Synthesis
6. **Audio** → Pygame → Playback

### Key Components

#### Speech Recognition (Vosk)
- Offline processing for privacy
- Real-time audio streaming
- Supports multiple languages

#### Knowledge Base (ChromaDB)
- Vector embeddings for semantic search
- Persistent storage across sessions
- Automatic data loading from Excel

#### Text-to-Speech (Edge TTS)
- High-quality natural voice synthesis
- Multiple voice options available
- Streaming audio generation

#### Audio Processing
- In-memory processing to avoid file permission issues
- Cross-platform compatibility
- Feedback prevention system

## 📊 Knowledge Base

### Data Sources
- Excel files with multiple sheets
- Q&A pairs extracted automatically
- Structured format: Question → Answer

### Supported Topics
- Bigship company overview
- Onboarding & registration
- Services & shipping options
- Pricing, payments & COD
- Vendor information
- Shipping processes

## 🔒 Privacy & Security

- **Offline Speech Recognition** - No audio sent to external servers
- **Local Data Storage** - All data stored locally
- **No Cloud Dependencies** - Works without internet (except TTS)
- **Secure Audio Processing** - In-memory processing prevents file leaks

## 🐛 Troubleshooting

### Common Issues

**Permission Denied Errors**
- Solution: The app now uses in-memory audio processing
- No temporary files created

**Speech Recognition Issues**
- Speak clearly and at normal pace
- Ensure microphone is working
- Check audio device settings
- Verify Vosk model is properly extracted

**ChromaDB Issues**
- Delete `chroma_db` folder and restart
- Check Excel file format (Column A = Questions, Column C = Answers)
- Ensure sufficient disk space

**Poor Answer Quality**
- Questions are processed semantically
- Try rephrasing your question
- Ensure question is related to Bigship services

**Audio Playback Issues**
- Check speaker settings
- Ensure pygame is installed correctly
- Restart the application

**Model Download Issues**
- Try alternative download methods
- Check internet connection
- Verify zip file integrity after download

### Performance Tips
- Use a quiet environment for better speech recognition
- Speak clearly and at normal pace
- Wait for the assistant to finish speaking before asking next question
- Ensure microphone is not muted

## 🔄 Updates & Maintenance

### Adding New Knowledge
1. Update the Excel file with new Q&A pairs
2. Delete the existing ChromaDB collection: `rm -rf chroma_db/`
3. Restart the application to reload data

### Changing Voice
- Modify `EDGE_VOICE` variable in `app.py`
- Available voices: `en-US-JennyNeural`, `en-US-GuyNeural`, etc.

### Customizing Responses
- Edit the greeting message in `GREETING_MESSAGE`
- Modify garbled speech indicators in `garbled_indicators`

## 🚀 Ready for Use

The voice assistant is now fully operational and ready for:

#### Immediate Use
- Customer support automation
- Bigship information queries
- Voice-based FAQ system
- Interactive knowledge base

#### Potential Deployments
- Customer service centers
- Sales team support
- Training and onboarding
- Public information kiosks

## 📈 Future Enhancements

### Potential Improvements
- **Multi-language Support** - Add support for other languages
- **Conversation Memory** - Remember previous interactions
- **Advanced NLP** - Better question understanding
- **Voice Biometrics** - User voice recognition
- **API Integration** - Connect to live Bigship data
- **Mobile App** - Create mobile version

### Scalability
- **Cloud Deployment** - Deploy to cloud platforms
- **Microservices** - Split into separate services
- **Load Balancing** - Handle multiple concurrent users
- **Database Scaling** - Use distributed databases

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Standards
- Follow PEP 8 style guidelines
- Add comments for complex logic
- Include error handling
- Write unit tests for new features

## 📄 License

This project is developed for Bigship's internal use. All rights reserved.

## 📞 Support

For technical support or questions about the voice assistant:
- Check the troubleshooting section
- Review the configuration settings
- Ensure all dependencies are installed correctly
- Verify Vosk model is properly downloaded and extracted

---

**🎯 Setup Complete: Bigship AI Voice Assistant is ready for production use!**

*Built with Python 3.10, VS Code, and modern AI technologies for Bigship's customer support automation.* 
