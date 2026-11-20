"""Render one original Arabic micro-lesson on CPU. No accounts needed."""
import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import random
import subprocess
import tempfile
from uuid import uuid4

import arabic_reshaper
from bidi.algorithm import get_display
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests

W, H = 720, 1280
NAVY, PAPER, MINT = '#102d3b', '#fcf6e8', '#a6ecd4'
LABELS = ['التحدّي', 'الفكرة', 'الحساب', 'جرّب بنفسك']


def lesson(r):
    kind = r.choice(['خصم', 'سرعة', 'وقت'])
    if kind == 'خصم':
        n, p = r.randrange(6, 31)*10, r.choice([10, 20, 30])
        d = n*p//100
        return 'كم تدفع بعد الخصم؟', 'النسب_المئوية', [
            (f'{p}%', f'ثمن كتاب {n} درهمًا. كم تدفع بعد خصم {p} بالمئة؟'),
            (f'{n} ÷ 10 = {n//10}', 'لإيجاد عشرة بالمئة من الثمن، اقسمه على عشرة.'),
            (f'{n} − {d} = {n-d}', f'قيمة الخصم {d} درهمًا. اطرحها من الثمن الأصلي لتحصل على ثمن البيع.'),
            (f'{2*n} × {p}%', f'لو تضاعف الثمن وبقيت نسبة الخصم نفسها، فكم توفر؟ الجواب: {2*d} درهمًا.')]
    if kind == 'سرعة':
        v, t = r.randrange(4, 13)*5, r.choice([2, 3, 4])
        return 'كيف تحسب متوسط السرعة؟', 'متوسط_السرعة', [
            (f'{v*t} km', f'قطعت حافلة {v*t} كيلومترًا في {t} ساعات. ما متوسط سرعتها؟'),
            ('km / h', 'نريد المسافة التي تقابل ساعة واحدة، فنقسم المسافة الكلية على الزمن الكلي.'),
            (f'{v*t} ÷ {t} = {v}', f'متوسط السرعة {v} كيلومترًا في الساعة. لا يعني ذلك أن السرعة كانت ثابتة.'),
            (f'{v} × 2', f'كم تقطع الحافلة في ساعتين بنفس المتوسط؟ الجواب: {2*v} كيلومترًا.')]
    n, mins, pause = r.choice([3, 4, 5]), r.choice([15, 20, 25]), r.choice([3, 5, 7])
    return 'خطّط لوقت المراجعة', 'تنظيم_الوقت', [
        (f'{n} × {mins}', f'لديك {n} جلسات مراجعة، مدة كل واحدة {mins} دقيقة. كم تحتاج من الوقت مع الاستراحات؟'),
        (f'{n} − 1 = {n-1}', 'ضع استراحة بين كل جلستين فقط. عدد الاستراحات أقل بواحد من عدد الجلسات.'),
        (f'{n*mins} + {(n-1)*pause}', f'إذا كانت الاستراحة {pause} دقائق، فالمدة الإجمالية {n*mins+(n-1)*pause} دقيقة.'),
        (f'+ {mins+pause}', f'ماذا لو أضفت جلسة أخرى؟ أضف استراحة وجلسة، أي {mins+pause} دقيقة.')]


def font(size, bold=False):
    candidates = [os.getenv('ARABIC_FONT'), 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf',
                  'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf']
    for name in filter(None, candidates):
        try:
            return ImageFont.truetype(name, size, layout_engine=ImageFont.Layout.BASIC)
        except OSError:
            pass
    raise RuntimeError('Set ARABIC_FONT to an Arabic TrueType font.')


def rtl(text):
    return get_display(arabic_reshaper.reshape(text), base_dir='R')


def slide(i, title, symbol, text, photo):
    im = Image.new('RGB', (W,H), NAVY)
    if photo:
        im = Image.blend(im, ImageOps.fit(photo, im.size), .16)
    d = ImageDraw.Draw(im)
    def ar(x,y,s,size,color,bold=False):
        d.text((x,y), rtl(s), font=font(size,bold), fill=color, anchor='ra')
    d.text((54,70),'ARARA   /   STUDY NOTES',font=font(21,True),fill=MINT)
    ar(666,150,title,41,PAPER,True)
    for k in range(4):
        x = 522-k*156
        d.rounded_rectangle((x,255,x+142,261),3,fill=MINT if k<=i else '#516771')
    d.rounded_rectangle((48,320,672,630),32,fill=MINT)
    d.text((75,350),f'EXERCISE    /    0{i+1}',font=font(19,True),fill=NAVY)
    d.text((360,492),symbol,font=font(62,True),anchor='mm',fill=NAVY)
    ar(659,716,LABELS[i],32,MINT,True)
    lines = ['']
    for word in text.split():
        candidate = (lines[-1]+' '+word).strip()
        if font(39).getlength(rtl(candidate))>602:
            lines.append(word)
        else:
            lines[-1] = candidate
    for j,line in enumerate(lines):
        ar(659,802+j*65,line,39,PAPER)
    d.line((54,1160,666,1160),fill='#647a80',width=2)
    ar(666,1188,'دفتر الطالب   /   درس قصير',24,MINT)
    d.text((54,1188),f'0{i+1} / 04',font=font(22),fill=PAPER)
    return im


def background():
    # Opt-in stock photography; never import the soundtrack of a stock clip.
    key = os.environ['PEXELS_API_KEY']
    resp = requests.get('https://api.pexels.com/v1/search', params={'query':'sand dunes landscape','orientation':'portrait','per_page':8},headers={'Authorization':key},timeout=20)
    resp.raise_for_status()
    item = random.choice(resp.json()['photos'])
    from io import BytesIO
    img = requests.get(item['src']['large'],timeout=30)
    img.raise_for_status()
    return Image.open(BytesIO(img.content)).convert('RGB'), f"Photo: {item['photographer']} / Pexels — {item['url']}"


def render(args):
    seed = args.seed if args.seed is not None else random.SystemRandom().getrandbits(63)
    title, tag, scenes = lesson(random.Random(seed))
    photo, credit = background() if args.pexels else (None, '')
    dest = Path(args.output); dest.mkdir(parents=True, exist_ok=True)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(dir=dest) as work:
        tmp=Path(work)
        for i,(symbol,text) in enumerate(scenes):
            slide(i,title,symbol,text,photo).save(tmp/'card.png')
            audio=['-f','lavfi','-i','anullsrc=r=44100:cl=mono','-t',str(max(6,math.ceil(len(text.split())/2)))]
            if args.voice:
                import edge_tts
                asyncio.run(edge_tts.Communicate(text,'ar-MA-JamalNeural').save(str(tmp/'voice.mp3')))
                audio=['-i','voice.mp3','-shortest']
            subprocess.run([ff,'-loglevel','error','-y','-loop','1','-framerate','24','-i','card.png',*audio,'-c:v','libx264','-threads','2','-preset','veryfast','-tune','stillimage','-pix_fmt','yuv420p','-c:a','aac','-ar','44100','-ac','1',f'{i}.mp4'],cwd=tmp,check=True)
        (tmp/'list.txt').write_text(''.join(f"file '{i}.mp4'\n" for i in range(4)))
        subprocess.run([ff,'-loglevel','error','-f','concat','-safe','0','-i','list.txt','-c','copy','-movflags','+faststart','lesson.mp4'],cwd=tmp,check=True)
        tags=['تعلم',tag,'دفتر_الطالب']
        meta=dict(seed=seed,title=title,description='\n'.join([scenes[0][1],credit,' '.join('#'+t for t in tags)]).strip(),tags=tags,scenes=scenes)
        (tmp/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
        job=dest/uuid4().hex[:12]; job.mkdir()
        for name in ['lesson.mp4','metadata.json']:
            (tmp/name).replace(job/name)
    return job


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed',type=int); p.add_argument('--output',default='output')
    p.add_argument('--voice',action='store_true'); p.add_argument('--pexels',action='store_true')
    p.add_argument('--publish',choices=['youtube','facebook'],nargs='+')
    a=p.parse_args(); job=render(a); print(job,flush=True)
    if a.publish:
        from publish import publish
        for target in a.publish:
            publish(job,target)
