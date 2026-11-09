import stable_whisper, json
L=json.load(open('lyrics.json'))
text='\n'.join(x['text'] for x in L)
m=stable_whisper.load_model('small',device='cpu')
r=m.align('vocals.wav',text,language='zh',original_split=True)
r.save_as_json('align.json')
for s in r.segments: print(round(s.start,2),round(s.end,2),s.text)
