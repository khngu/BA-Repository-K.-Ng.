################################ Begin importing all libraries ##################################
from flask import Flask, request, jsonify, send_file
from google.cloud import texttospeech
from openai import OpenAI
import base64
import requests
import os
import pygame
import tempfile
import vosk
import sounddevice as sd
import queue
import time
import json
import wave
import threading

##################################################################################################
# Create flask application
app = Flask(__name__)

# Thread for playing loading sound
loading_thread = None

# Default System Message for Chatbot
DEFAULT_SYSTEM_MESSAGE = {
    "role": "system",
    "content": "Du bist mein Assistent und gibst mir Antworten zu allem was ich will! Du antwortest immer in klaren und nicht so langen Texten, sodass ich die generierte Antwort in Text to Speech umwandeln kann!"
}

# initialize global chat history with default system message declared above
chat_history = [DEFAULT_SYSTEM_MESSAGE]

###################################### Declare API Keys ########################################

# Google API Key
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "PATH_TO_GOOGLE_API_KEY.json" # api-key saved as json

# OpenAI API Key
api_key = "***********************" # define private API-key

################################################################################################

################################################################################################
#### Function: send_image_to_openai()
### Parameter: image_path = path of the image to be sent to the api; status = current application mode
# Description: send an image to openai's api, in order to analyze the image and get respond
################################################################################################

def send_image_to_openai(image_path, status):
    if status == "Analyze_Text": 
        systemRole = "Du bist mein Assistent und analysierst und liest mir den im Fokus liegenden Objekt auf dem Bild vor, weil ich sehr schlecht sehen kann!"
        userQuestion = "Lese mir den Text genau so vor wie du es siehst!"
    elif status == "Analyze_Object": 
        systemRole = "Du bist mein Assistent und sagst mir was du im Bild siehst, weil ich sehr schlecht sehen kann!"
        userQuestion = getMicrophoneInput()

    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "system",
                "content": systemRole
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": userQuestion
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 2000
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()

################################################################################################
################################ send_image_to_openai() END ####################################
################################################################################################

################################################################################################
#### Function: generate_tts()
### Parameter: answer = contains to be synthesized text
# Description: synthesize an audio file with given string with googles TTS
################################################################################################
def generate_tts(answer):
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=answer)

    voice = texttospeech.VoiceSelectionParams(
        language_code='de-DE',
        name='de-DE-Wavenet-B'
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        effects_profile_id=['small-bluetooth-speaker-class-device'],
        speaking_rate=1,
        pitch=1
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
        temp_audio_file.write(response.audio_content)
        temp_audio_file_path = temp_audio_file.name
        print('Audio content written SUCCESSFULLY')

    # Stop the loading sound right before playing the TTS audio
    stop_loading_sound()

    # Initialize pygame mixer
    pygame.mixer.init()

    # Load and play the MP3 file
    pygame.mixer.music.load(temp_audio_file_path)
    pygame.mixer.music.play()

    # Wait until the audio is finished playing
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    # Stop the mixer and delete the temporary file
    pygame.mixer.music.stop()
    pygame.mixer.quit()

    # Wait a little bit to ensure the file is no longer in use
    time.sleep(1)

    os.remove(temp_audio_file_path)
################################################################################################
###################################### generate_tts() END ######################################
################################################################################################

################################################################################################
#### Function: send_text_to_openai()
# Description: send text to openai's api, in order to chat with the api
################################################################################################
def send_text_to_openai():
    spokenInput = getMicrophoneInput()
    
    # Füge die neue Nachricht zur Chat-Historie hinzu
    chat_history.append({"role": "user", "content": spokenInput})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4o",
        "messages": chat_history,
        "max_tokens": 2000
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    
    # add answer to chat history
    response_data = response.json()
    if 'choices' in response_data and len(response_data['choices']) > 0:
        assistant_message = response_data['choices'][0]['message']['content']
        chat_history.append({"role": "assistant", "content": assistant_message})
    
    return response_data
################################################################################################
################################## send_text_to_openai() END ###################################
################################################################################################

################################################################################################
#### Function: playModeSound()
### Parameter: audiofileName = data name of audio file; loop = determine to loop audio file
# Description: play User Interface Sounds
################################################################################################
def playModeSound(audiofileName, loop=False):
    # Initialize pygame mixer
    pygame.mixer.init()
    systemSoundPath = r"SystemSounds"
    audiofilePath = os.path.join(systemSoundPath, f"System_{audiofileName}.mp3")
    print(f"Attempting to play: {audiofilePath}, loop={loop}")
    try:
        pygame.mixer.music.load(audiofilePath)
        pygame.mixer.music.play(loops=-1 if loop else 0)
        print(f"Playing {audiofileName}")
        # Wait until the audio is finished playing (if not looping)
        if not loop:
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
    except pygame.error as e:
        print(f"Error loading or playing sound: {e}")
    finally:
        if not loop:
            pygame.mixer.quit()
################################################################################################
##################################### playModeSound() END ######################################
################################################################################################

################################################################################################
#### Function: start_loading_sound() & stop_loading_sound
# Description: start or stop loading sound, used in order to notify user that process is still going
################################################################################################

def start_loading_sound():
    global loading_thread
    loading_thread = threading.Thread(target=playModeSound, args=("Loading", True))
    print("Loading")
    loading_thread.start()

def stop_loading_sound():
    if loading_thread and loading_thread.is_alive():
        pygame.mixer.music.stop()
        loading_thread.join()
        pygame.mixer.quit()
################################################################################################
####################### start_loading_sound() & stop_loading_sound END #########################
################################################################################################

################################################################################################
#### Function: getMicrophoneInput()
# Description: start listening via microphone, save it as an audio file, send it to openAI's
############## whisperAI (SpeechToText) and return the transcribed text
################################################################################################
def getMicrophoneInput():
    q = queue.Queue()

    def callback(indata, frames, time, status):
        q.put(bytes(indata))  # Add audio data to the queue

    # Initialize vosk model
    model = vosk.Model("vosk-model-small-de-0.15")
    samplerate = 16000
    device = sd.default.device

    last_sound_time = time.time()
    start_time = time.time()
    file_name = "transcribe_audio.wav"  # Save as WAV for compatibility

    # Open the audio file for writing
    with wave.open(file_name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)

        # Start recording the audio
        with sd.RawInputStream(samplerate=samplerate, blocksize=8000, device=device[0], dtype='int16', channels=1, callback=callback):

            playModeSound("Mic_Recording")

            rec = vosk.KaldiRecognizer(model, samplerate)

            while True:
                data = q.get()
                wf.writeframes(data)  # Write the audio data to the file

                if rec.AcceptWaveform(data):
                    result = rec.Result()
                    if isinstance(result, str):
                        result_dict = json.loads(result)
                        text = result_dict.get("text", "")
                        if text:
                            last_sound_time = time.time()  # Update the time if speech is detected

                # Stop recording after 5 seconds and 2 seconds of silence
                if time.time() - start_time > 5 and time.time() - last_sound_time > 2:
                    break

    # Audio recording end
    print(f"Audio file written successfully. File saved as '{file_name}'.")

    # Play loading sound after recording ends
    start_loading_sound()

    # Transcribe the audio using OpenAI
    client = OpenAI(api_key=api_key)

    with open(file_name, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )

    # Return the transcribed text
    return transcription.text

################################################################################################
################################## getMicrophoneInput() END ####################################
################################################################################################

################################################################################################
#### Route: /upload (POST)
### Description: Endpoint for uploading files (images), processes the image based on the provided status.
### Parameter: 
# - 'file': uploaded file (image) from the request.
# - 'status': mode which specifies if the image should be analyzed for text or objects.
################################################################################################
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    # Delete the previous image if it exists
    file_path = 'received_image.jpg'
    if os.path.exists(file_path):
        os.remove(file_path)
        print("Deleted previous image.")

    file.save(file_path)
    print(f"Saved new image to {file_path}")

    status = request.form.get('status')
    if status in ["Analyze_Text", "Analyze_Object"]:
        print(f"Received status: {status}")
        
        # Start loading sound in a separate thread
        start_loading_sound()
        
        response = send_image_to_openai(file_path, status)

        # Extract the message content from the OpenAI response
        message_content = response['choices'][0]['message']['content']

        # Save the message content to a string for further use
        global answer_string
        answer_string = message_content

        # Print the answer for debugging purposes
        print(f"Generated Answer: {answer_string}")

        generate_tts(answer_string)

        return "Image processed and response saved.", 200

    elif status == "Chatbot":
        print(f"Received status: {status}")

        response = send_text_to_openai()

        # Extract the message content from the OpenAI response
        message_content = response['choices'][0]['message']['content']

        # Print the answer for debugging purposes
        print(f"Generated Answer: {message_content}")

        generate_tts(message_content)

        return "Audio processed and response saved.", 200
################################################################################################
###################################### upload_file() END #######################################
################################################################################################

################################################################################################
#### Route: /view_image (GET)
### Description: Endpoint for viewing the uploaded image. Sends the image file if it exists.
################################################################################################
@app.route('/view_image', methods=['GET'])
def view_image():
    file_path = 'received_image.jpg'
    if os.path.exists(file_path):
        print("Image exists, sending file.")
        return send_file(file_path, mimetype='image/jpeg')
    else:
        print("Image not found.")
        return "Image not found", 404
################################################################################################
##################################### view_image() END #########################################
################################################################################################

################################################################################################
#### Route: /mode (POST)
### Description: Endpoint for changing the application mode. Plays a mode-specific sound.
### Parameter: 
# - 'mode': mode string that specifies the new mode sound to play.
################################################################################################
@app.route('/mode', methods=['POST'])
def mode_change():
    mode = request.form.get('mode')
    if not mode:
        return jsonify({'error': 'No mode provided'}), 400
    print("Mode Changed to:", mode)
    playModeSound(mode)
    return jsonify({'message': f'Mode changed to {mode}'}), 200
################################################################################################
##################################### mode_change() END ########################################
################################################################################################

################################################################################################
#### Main Function
# Description: This section initializes the global answer string, plays the startup sound, and 
#              starts the Flask app.
################################################################################################
if __name__ == '__main__':
    # Initialize the global answer string
    answer_string = ""
    
    # Play the startup sound
    playModeSound("Start")
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000)
################################################################################################
###################################### MAIN FUNCTION END #######################################
################################################################################################
