#!/usr/bin/env python3
"""Optional local PocketSphinx word/phone guide; no game assets or native programs.

Install pocketsphinx in the helper Python, not Blender's Python. This is an
editable timing estimate against the user's transcript, never finished acting.
"""
import argparse
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import re
import sys
import wave


def align(raw, text):
    import numpy as np
    from pocketsphinx import Decoder
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'setup'))
    from fighter_caf_mouth import wav_info
    info = wav_info(raw)
    if info['seconds'] > 30 or not isinstance(text, str) or len(text) > 500:
        raise ValueError('Alignment supports a short voice and transcript')
    words = re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower().replace('’', "'"))
    if not 1 <= len(words) <= 50:
        raise ValueError('Enter the words spoken in the voice track')
    # bestpath may return a truncated path even with a forced grammar. Always
    # check full word coverage; keep silence arcs for pauses between phrases.
    decoder = Decoder(lm=None, loglevel='ERROR', beam=1e-100, wbeam=1e-100,
                      pbeam=1e-100, bestpath=False, lw=1., wip=1.)
    inferred = {}
    for word in words:
        if decoder.lookup_word(word):
            continue
        if word.endswith("'s") and decoder.lookup_word(word[:-2]):
            pronunciation = decoder.lookup_word(word[:-2]) + ' Z'
            decoder.add_word(word, pronunciation, True)
            inferred[word] = pronunciation
        else:
            raise ValueError('No local pronunciation for %r; use a dictionary spelling' % word)
    with wave.open(io.BytesIO(raw), 'rb') as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2')
    count = round(len(pcm) * 16000 / info['sample_rate'])
    audio = np.interp(np.arange(count) * info['sample_rate'] / 16000,
                      np.arange(len(pcm)), pcm).astype('<i2').tobytes()
    transcript = ' '.join(words)
    decoder.set_align_text(transcript)
    decoder.start_utt(); decoder.process_raw(audio, full_utt=True); decoder.end_utt()
    hypothesis = decoder.hyp()
    if not hypothesis or hypothesis.hypstr != transcript:
        raise ValueError('Automatic alignment omitted words; use the waveform/manual keys')
    decoder.set_alignment()
    decoder.start_utt(); decoder.process_raw(audio, full_utt=True); decoder.end_utt()
    result = []
    for word in decoder.get_alignment():
        result.append(dict(word=word.name, start=word.start / 100,
                           end=(word.start + word.duration) / 100,
                           phones=[dict(phone=p.name, start=p.start / 100,
                                        end=(p.start + p.duration) / 100) for p in word]))
    actual = [re.sub(r'\(\d+\)$', '', r['word']) for r in result
              if r['word'] not in ('<s>', '</s>', '<sil>', '[NOISE]')]
    if actual != words:
        raise ValueError('Sub-word alignment omitted words; manual correction required')
    return dict(schema='fighter-speech-cues-1', source_sha256=hashlib.sha256(raw).hexdigest(),
                transcript=transcript, seconds=info['seconds'], words=result,
                engine='pocketsphinx', engine_version=importlib.metadata.version('pocketsphinx'),
                inferred_pronunciations=inferred,
                notice='Estimated timing and coarse native poses; review every closure and vowel manually')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wav', required=True); p.add_argument('--text', required=True)
    p.add_argument('--out', required=True); args = p.parse_args()
    target = Path(args.out)
    if target.exists():
        raise ValueError('Choose a new cue filename')
    result = align(Path(args.wav).read_bytes(), args.text)
    with target.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print('Aligned %d words; review the estimated guide' % len(result['transcript'].split()))


if __name__ == '__main__':
    main()
