#!/usr/bin/env python3
"""习题2-37：四球一维完全弹性碰撞。Python 3.9+，Pillow，FFmpeg。
python four_balls.py --video four_balls.mp4
python four_balls.py --preview  # 空格暂停/继续，R重播
python four_balls.py --check    # 仅验证物理计算，不需要Pillow或FFmpeg
"""
from fractions import Fraction as F
from pathlib import Path
import argparse
import math
import shutil
import subprocess

M = (F(2), F(2), F(1), F(1))
X0 = (F(0), F(3), F(6), F(9))
U0 = (F(1), F(0), F(0), F(0))
R = F(3, 5)
WIDTH, HEIGHT, FPS, DURATION = 1280, 720, 24, 28
COLORS = ('#5ba5ff', '#38d6bb', '#ffbe60', '#c299ff')


def conserved(u):
    return sum(m*v for m,v in zip(M,u)), sum(m*v*v/2 for m,v in zip(M,u))


def simulate():
    """精确计算下一次接触时刻；分数运算避免时间步穿透和累计误差。
    此题等间距初态只有独立的两球碰撞，不涉及多球同时接触。
    """
    x, u, t, events = list(X0), list(U0), F(0), []
    for _ in range(100):
        candidates = []
        for i in range(3):
            if u[i] > u[i+1]:
                dt = (x[i+1]-x[i]-2*R)/(u[i]-u[i+1])
                assert dt >= 0
                candidates.append((dt, i))
        if not candidates:
            return events
        dt, i = min(candidates)
        x = [a+b*dt for a,b in zip(x,u)]
        t += dt
        before = tuple(u)
        a,b = u[i:i+2]
        p,q = M[i:i+2]
        u[i] = ((p-q)*a+2*q*b)/(p+q)
        u[i+1] = (2*p*a+(q-p)*b)/(p+q)
        assert conserved(u) == conserved(U0)
        assert u[i+1]-u[i] == a-b  # 恢复系数为1
        assert all(x[j+1]-x[j] >= 2*R for j in range(3))
        events.append(dict(t=t, x=tuple(x), u=tuple(u), before=before, pair=i))
    raise RuntimeError('碰撞次数超过上限')


EVENTS = simulate()


def state(t):
    """在相邻碰撞之间做匀速运动；碰撞瞬间采用碰撞后的速度。"""
    x, u, start, count = X0, U0, 0., 0
    for e in EVENTS:
        if float(e['t']) > t+1e-10:
            break
        x, u, start = e['x'], e['u'], float(e['t'])
        count += 1
    return [float(a)+float(b)*(t-start) for a,b in zip(x,u)], u, count


def fraction(v):
    return str(v)


def physical_time(video_time):
    # 开头静止2秒，22秒播放0~12秒物理过程，末尾停留4秒。
    return max(0., min(12., (video_time-2)*12/22))


class Renderer:
    def __init__(self, font_path=None):
        from PIL import Image, ImageDraw, ImageFont
        self.Image, self.ImageDraw = Image, ImageDraw
        candidates = [font_path] if font_path else []
        candidates += ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                       'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf',
                       '/System/Library/Fonts/PingFang.ttc']
        self.font_path = next((p for p in candidates if p and Path(p).is_file()), None)
        if not self.font_path:
            raise SystemExit('未找到中文字体，请使用 --font 指定中文.ttf或.ttc字体文件。')
        self.fonts = {n: ImageFont.truetype(self.font_path, n) for n in [16,18,20,22,24,28,32,42]}

    def frame(self, seconds):
        im = self.Image.new('RGB', (WIDTH, HEIGHT), '#0c1323')
        d = self.ImageDraw.Draw(im)
        def text(x,y,s,size=22,color='#ecf2ff',anchor=None):
            d.text((x,y),s,font=self.fonts[size],fill=color,anchor=anchor)
        def box(rect,fill='#172238',outline=None):
            d.rounded_rectangle(rect, radius=14, fill=fill, outline=outline, width=2)
        t = physical_time(seconds)
        xs, us, n = state(t)
        text(48,24,'物理动画  /  习题 2-37',18,'#7e9abf')
        text(48,55,'四球的一维完全弹性碰撞',42)
        text(50,118,'光滑水平面  ·  等半径  ·  质量从左到右为 2m、2m、m、m',22,'#a9bad3')
        box((1005,34,1232,111))
        text(1118,53,f't = {t:05.2f}',28,anchor='mt')
        text(1118,87,'归一化时间',16,'#a9bad3',anchor='mt')
        # 横轴始终固定，向右为正；球半径与坐标尺使用相同的比例。
        scale, left, cy = 45, 88, 300
        d.line((48,328,1232,328),fill='#61758e',width=3)
        for x in range(0,25,2):
            px = left+x*scale
            d.line((px,329,px,337),fill='#61758e',width=2)
            text(px,345,str(x),16,'#7e9abf',anchor='mt')
        text(1232,375,'x / L →',18,'#7e9abf',anchor='rt')
        if n and abs(t-float(EVENTS[n-1]['t'])) < .27:
            j = EVENTS[n-1]['pair']
            for i in (j,j+1):
                px=left+xs[i]*scale
                d.ellipse((px-35,cy-35,px+35,cy+35),outline='#ffffff',width=3)
        for i,(x,u,c) in enumerate(zip(xs,us,COLORS)):
            px = left+x*scale
            r = float(R)*scale
            d.ellipse((px-r,cy-r,px+r,cy+r),fill=c)
            text(px,cy,str(i+1),24,'#0c1323',anchor='mm')
            text(px,247,'2m' if i<2 else 'm',20,c,anchor='mm')
            if u:
                length=60*float(u)
                d.line((px,208,px+length,208),fill=c,width=3)
                d.polygon([(px+length,208),(px+length-9,203),(px+length-9,213)],fill=c)
        box((48,409,1232,502))
        text(70,421,'各球当前速度 / v',18,'#a9bad3')
        for i,(u,c) in enumerate(zip(us,COLORS)):
            text(345+i*236,450,f'{i+1}号   {fraction(u)}',28,c,anchor='mm')
        text(70,465,'向右为正',16,'#7e9abf')
        for k,e in enumerate(EVENTS):
            x=48+k*300
            done=k<n
            box((x,522,x+284,605),'#203047' if done else '#111c30',COLORS[e['pair']] if done else None)
            text(x+16,533,f"第{k+1}次   {e['pair']+1} ↔ {e['pair']+2}",22,'#ecf2ff' if done else '#667e9e')
            text(x+16,570,f"t = {float(e['t']):.2f}" + ('   已发生' if done else '   等待'),18,'#a9bad3')
        p,ke=conserved(us)
        text(50,626,f'动量 P/(mv) = {p}     动能 E/(mv²) = {ke}     全过程守恒',20,'#76dcc1')
        caption='初态：仅1号球以速度 v 向右运动，其余三球静止。'
        if n:
            caption=['1、2号等质量，交换速度。','2号撞3号：2号速度为 v/3，3号速度为 4v/3。',
                     '3、4号等质量，交换速度；2号继续追赶3号。',
                     '最终：0、v/9、4v/9、4v/3；速度依次增大，不再碰撞。'][n-1]
        text(50,665,caption,22)
        return im


def check():
    assert [e['pair'] for e in EVENTS] == [0,1,2,1]
    assert EVENTS[-1]['u'] == (F(0),F(1,9),F(4,9),F(4,3))
    for k in range(1201):
        xs,us,_=state(k/100)
        assert all(xs[j+1]-xs[j] >= float(2*R)-1e-9 for j in range(3))
        assert conserved(us)==(F(2),F(1))
    for i,e in enumerate(EVENTS,1):
        print(f"第{i}次: t={e['t']}, 球{e['pair']+1}与{e['pair']+2}, u/v={[str(v) for v in e['u']]}")
    print('通过：碰撞顺序、最终速度、动量守恒、动能守恒、恢复系数和球体无穿透。')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',nargs='?',const='four_balls.mp4',help='导出28秒MP4')
    parser.add_argument('--preview',action='store_true',help='窗口播放（需Tkinter）')
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--font',help='中文字体路径')
    args=parser.parse_args()
    check()
    if args.check and not (args.video or args.preview): return
    if not (args.video or args.preview):
        parser.print_help(); return
    renderer=Renderer(args.font)
    if args.video:
        ffmpeg=shutil.which('ffmpeg')
        if not ffmpeg: raise SystemExit('请先安装FFmpeg并加入PATH。')
        command=[ffmpeg,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
                 '-s',f'{WIDTH}x{HEIGHT}','-r',str(FPS),'-i','-', '-an',
                 '-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',
                 '-movflags','+faststart',args.video]
        with subprocess.Popen(command,stdin=subprocess.PIPE) as proc:
            for k in range(FPS*DURATION): proc.stdin.write(renderer.frame(k/FPS).tobytes())
            proc.stdin.close()
            if proc.wait(): raise SystemExit('视频编码失败。')
        print('视频已保存：',args.video)
    if args.preview:
        import tkinter as tk
        from PIL import ImageTk
        root=tk.Tk(); root.title('四球碰撞 | 空格暂停/继续 | R重播')
        label=tk.Label(root); label.pack()
        playback={'k':0,'paused':False}
        def toggle(event): playback['paused']=not playback['paused']
        def reset(event): playback.update(k=0,paused=False)
        root.bind('<space>',toggle); root.bind('r',reset); root.bind('R',reset)
        def tick():
            frame=ImageTk.PhotoImage(renderer.frame(playback['k']/FPS))
            label.configure(image=frame); label.image=frame
            if not playback['paused']: playback['k']=min(playback['k']+1,FPS*DURATION-1)
            root.after(round(1000/FPS),tick)
        tick(); root.mainloop()


if __name__=='__main__': main()
