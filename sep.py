import torch, soundfile as sf, numpy as np
from demucs.pretrained import get_model
from demucs.apply import apply_model
import subprocess
subprocess.run(['ffmpeg','-y','-v','error','-i','song.mp3','-ar','44100','-ac','2','song44.wav'])
wav,sr=sf.read('song44.wav',dtype='float32'); wav=torch.tensor(wav.T)
m=get_model('htdemucs'); m.eval()
ref=wav.mean(0); w=(wav-ref.mean())/ref.std()
torch.set_num_threads(2)
with torch.no_grad(): src=apply_model(m,w[None],split=True,overlap=0.25,progress=False)[0]
src=src*ref.std()+ref.mean()
v=src[m.sources.index('vocals')].numpy().T
sf.write('vocals.wav',v,sr); print('ok',v.shape)
