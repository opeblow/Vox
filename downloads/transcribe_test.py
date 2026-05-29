import whisper

import os
os.environ['PATH'] += r';C:\Users\user\AppData\Local\ffmpeg\bin'

audio_path = r'C:\Users\user\Documents\vox\downloads\recording.m4a'
print('Loading audio...')
audio = whisper.load_audio(audio_path)
duration = len(audio) / whisper.audio.SAMPLE_RATE
print(f'Duration: {duration:.1f}s ({duration/60:.1f} min)')

print('Loading model (tiny)...')
model = whisper.load_model('tiny')
print('Transcribing...')
result = model.transcribe(audio_path, fp16=False)
print(f"Detected language: {result.get('language', 'unknown')}")
text = result.get('text', '').strip()
print(f'Transcript length: {len(text)} chars')
if text:
    out_path = r'C:\Users\user\Documents\vox\downloads\transcript.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'Full transcript saved to: {out_path}')
    print(f'Total length: {len(text)} chars')
    print('---FIRST 2000 CHARS---')
    print(text[:2000])
