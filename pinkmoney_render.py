#!/usr/bin/env python3
import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import subprocess, os, time, re, argparse, tempfile, shutil

W, H   = 1920, 1080
FPS    = 30
COL_W  = 960
PAD_X  = 40
LINE_H = 30
CODE_TOP = 40
CODE_BOT = H - 16
VISIBLE_LINES = (CODE_BOT - CODE_TOP) // LINE_H
CONSOLAS = "/mnt/c/Windows/Fonts/consola.ttf"

C_BG      = (10, 12, 16, 170)
C_DEFAULT = (212, 212, 212, 255)
C_KEYWORD = (86, 156, 214, 255)
C_TYPE    = (78, 201, 176, 255)
C_NUMBER  = (181, 206, 168, 255)
C_STRING  = (206, 145, 120, 255)
C_FUNC    = (220, 220, 170, 255)
C_PUNCT   = (150, 150, 150, 255)
C_LINENO  = (65, 65, 65, 255)

GLSL_KEYWORDS = {'void','if','else','for','while','return','in','out','inout','uniform','varying','attribute','const'}
GLSL_TYPES    = {'float','vec2','vec3','vec4','mat2','mat3','mat4','int','bool','sampler2D'}
GLSL_BUILTINS = {'sin','cos','atan','length','mix','clamp','smoothstep','dot','cross','normalize','abs','pow','sqrt','fract','floor','mod','step','min','max','reflect','refract','texture2D','texture'}
SC_KEYWORDS   = {'var','arg','true','false','nil','SynthDef','Score','Env','EnvGen','SinOsc','Out','Mix','Pan2','FreeVerb','DelayC','BPF','Dust','PinkNoise','WhiteNoise','TRand','Trig1','Impulse','LFNoise1','LFSaw','LFTri','Saw','Pulse','HPF','LPF'}
SC_METHODS    = {'ar','kr','new','add','range','asBytes','writeOSCFile','perc','linen','do','collect','postln','play','fork','value'}

def tokenize_glsl(line):
    tokens = []
    for m in re.finditer(r'(\b\d+\.?\d*\b|[A-Za-z_]\w*|[^\w\s]|\s+)', line):
        tok = m.group()
        if re.match(r'^\d+\.?\d*$', tok): tokens.append((tok, C_NUMBER))
        elif tok in GLSL_KEYWORDS:         tokens.append((tok, C_KEYWORD))
        elif tok in GLSL_TYPES:            tokens.append((tok, C_TYPE))
        elif tok in GLSL_BUILTINS:         tokens.append((tok, C_FUNC))
        elif tok in '{}()[];,':            tokens.append((tok, C_PUNCT))
        else:                              tokens.append((tok, C_DEFAULT))
    return tokens

def tokenize_sc(line):
    tokens = []
    for m in re.finditer(r'(\b\d+\.?\d*\b|\\[A-Za-z_]\w*|[A-Za-z_]\w*|[^\w\s\'\\]|\s+)', line):
        tok = m.group()
        if tok.startswith('\\'):            tokens.append((tok, C_STRING))
        elif re.match(r'^\d+\.?\d*$', tok): tokens.append((tok, C_NUMBER))
        elif tok in SC_KEYWORDS:            tokens.append((tok, C_KEYWORD))
        elif tok in SC_METHODS:             tokens.append((tok, C_FUNC))
        elif tok in '{}()[];,|':            tokens.append((tok, C_PUNCT))
        else:                               tokens.append((tok, C_DEFAULT))
    return tokens

def strip_comments(code, style='glsl'):
    result = []
    for line in code.strip().split('\n'):
        s = line.strip()
        if style == 'glsl' and (s.startswith('//') or s.startswith('#version')):
            continue
        if style == 'sc' and s.startswith('//'):
            continue
        result.append(line)
    return result

def wrap_lines(lines, col_width, font):
    avail = col_width - PAD_X - 48
    result = []
    for line in lines:
        if font.getlength(line) <= avail:
            result.append(line)
            continue
        indent     = len(line) - len(line.lstrip())
        cont_pfx   = ' ' * (indent + 4)
        cont_avail = avail - font.getlength(cont_pfx)
        remaining  = line
        first      = True
        while remaining:
            cur_avail = avail if first else cont_avail
            lo, hi = 1, len(remaining)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if font.getlength(remaining[:mid]) <= cur_avail:
                    lo = mid
                else:
                    hi = mid - 1
            chunk     = remaining[:lo]
            remaining = remaining[lo:]
            if not first:
                chunk = cont_pfx + chunk.lstrip()
            result.append(chunk)
            first = False
    return result

def scroll_offset(frame_idx, total_frames, total_lines):
    if total_lines <= VISIBLE_LINES:
        return 0.0
    extra   = total_lines - VISIBLE_LINES
    start_f = int(total_frames * 0.1)
    end_f   = int(total_frames * 0.9)
    if frame_idx <= start_f:
        return 0.0
    if frame_idx >= end_f:
        return float(extra)
    return extra * (frame_idx - start_f) / (end_f - start_f)

def render_frame(base_img, glsl_lines, sc_lines, font_code, font_title, frame_idx, total_frames):
    overlay = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, 0, W, H], fill=C_BG)
    img  = Image.alpha_composite(base_img.convert('RGBA'), overlay)
    draw = ImageDraw.Draw(img)

    def draw_column(lines, tokenizer, x_start, title, title_color):
        draw.text((x_start + PAD_X, 14), title, font=font_title, fill=title_color)
        offset_px = scroll_offset(frame_idx, total_frames, len(lines)) * LINE_H
        col_img   = Image.new('RGBA', (COL_W, H), (0, 0, 0, 0))
        col_draw  = ImageDraw.Draw(col_img)
        for i, line in enumerate(lines):
            cy = CODE_TOP + i * LINE_H - offset_px
            if cy + LINE_H < CODE_TOP or cy > CODE_BOT:
                continue
            col_draw.text((PAD_X, cy), f"{i+1:2d}", font=font_code, fill=C_LINENO)
            cx = PAD_X + 48
            for tok, color in tokenizer(line):
                col_draw.text((cx, cy), tok, font=font_code, fill=color)
                cx += font_code.getlength(tok)
        cropped = col_img.crop((0, CODE_TOP, COL_W, CODE_BOT))
        img.paste(cropped, (x_start, CODE_TOP), cropped)

    draw_column(glsl_lines, tokenize_glsl, 0,     "[ fragment.glsl ]",     (120, 255, 120, 255))
    draw_column(sc_lines,   tokenize_sc,   COL_W, "[ supercollider.scd ]", (120, 200, 255, 255))
    return img.convert('RGB')

def render_audio_nrt(osc_path, output_wav, duration):
    tmpdir = tempfile.mkdtemp()
    silent = os.path.join(tmpdir, 'silent.wav')
    subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i',
                    f'anullsrc=r=44100:cl=stereo', '-t', str(duration + 0.5), silent],
                   capture_output=True)
    subprocess.run(['scsynth', '-N', osc_path, silent, output_wav,
                    '44100', 'wav', 'int16', '-o', '2'],
                   timeout=120, capture_output=True)
    shutil.rmtree(tmpdir)
    return os.path.exists(output_wav)

VERT_SRC = """
#version 330
in vec2 in_vert;
out vec2 v_uv;
void main() {
    v_uv = in_vert * 0.5 + 0.5;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

def render_video(glsl_src, sc_src, output_mp4, audio_wav=None, duration=30):
    font_code  = ImageFont.truetype(CONSOLAS, 22)
    font_title = ImageFont.truetype(CONSOLAS, 15)
    glsl_lines = wrap_lines(strip_comments(glsl_src, 'glsl'), COL_W, font_code)
    sc_lines   = wrap_lines(strip_comments(sc_src,   'sc'),   COL_W, font_code)
    total_frames = FPS * duration
    print(f"[render] GLSL:{len(glsl_lines)}L  SC:{len(sc_lines)}L  visible:{VISIBLE_LINES}L")

    ctx  = moderngl.create_standalone_context()
    prog = ctx.program(vertex_shader=VERT_SRC, fragment_shader=glsl_src)
    fbo  = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    fbo.use()
    verts = np.array([[-1,-1],[1,-1],[-1,1],[1,-1],[1,1],[-1,1]], dtype='f4')
    vao   = ctx.simple_vertex_array(prog, ctx.buffer(verts), 'in_vert')

    tmpdir = tempfile.mkdtemp()
    t0 = time.time()
    for i in range(total_frames):
        if 'u_time' in prog:
            prog['u_time'] = i / FPS
        ctx.clear(0, 0, 0)
        vao.render()
        data = fbo.read(components=4)
        img  = Image.frombytes('RGBA', (W, H), data).transpose(Image.FLIP_TOP_BOTTOM)
        img  = render_frame(img, glsl_lines, sc_lines, font_code, font_title, i, total_frames)
        img.save(f"{tmpdir}/f_{i:05d}.png")
        if i % 60 == 0:
            print(f"  {i}/{total_frames} ({i/total_frames*100:.0f}%) {time.time()-t0:.0f}s")

    print(f"[render] encoding...")
    cmd = ['ffmpeg', '-y', '-framerate', str(FPS), '-i', f"{tmpdir}/f_%05d.png"]
    if audio_wav and os.path.exists(audio_wav):
        cmd += ['-i', audio_wav, '-c:a', 'aac', '-shortest']
    cmd += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', output_mp4]
    subprocess.run(cmd, check=True, capture_output=True)
    shutil.rmtree(tmpdir)
    print(f"[render] done {time.time()-t0:.1f}s  {os.path.getsize(output_mp4)//1024}KB")
    return output_mp4

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--glsl',     required=True)
    parser.add_argument('--sc',       required=True)
    parser.add_argument('--osc',      default=None)
    parser.add_argument('--output',   required=True)
    parser.add_argument('--duration', type=int, default=30)
    parser.add_argument('--no-audio', action='store_true')
    args = parser.parse_args()

    glsl_src = open(args.glsl).read()
    sc_src   = open(args.sc).read()

    audio_wav = None
    if not args.no_audio:
        osc_path  = args.osc or args.output.replace('.mp4', '.osc')
        audio_wav = args.output.replace('.mp4', '.wav')
        if not (args.osc and os.path.exists(args.osc)):
            print("[audio] 需要 --osc 参数指定已生成的 OSC score 文件")
            exit(1)
        ok = render_audio_nrt(osc_path, audio_wav, args.duration)
        if not ok:
            audio_wav = None

    render_video(glsl_src, sc_src, args.output, audio_wav, args.duration)
