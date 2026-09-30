#!/usr/bin/env python3
"""Bornite Sweep — neon minesweeper arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/BORNITE_SWEEP_ElbowOS.mp4")
TITLE, HANDLE = "BORNITE SWEEP", "x.com/ElbowOS"

INK = (10, 4, 18)
PLUM = (36, 12, 48)
COPPER = (232, 118, 46)
TEAL = (28, 214, 186)
MAG = (255, 68, 168)
GOLD = (255, 206, 72)
LIME = (140, 255, 90)
CYAN = (70, 210, 255)
ROSE = (255, 96, 128)
VIO = (168, 92, 255)
WHITE = (248, 240, 255)
FOG = (210, 186, 220)
NUMC = {1: LIME, 2: CYAN, 3: MAG, 4: GOLD, 5: ROSE, 6: TEAL, 7: VIO, 8: WHITE}

COLS, ROWS, MINES = 8, 11, 14
MARGIN_X, TOP, BOT = 70, 250, 120


class Game:
    def __init__(self, record=False):
        self.record = record
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY and not record else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            self.screen = pygame.Surface((W, H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.SysFont("dejavusans", 52, bold=True)
        self.font_md = pygame.font.SysFont("dejavusans", 34, bold=True)
        self.font_sm = pygame.font.SysFont("dejavusans", 26)
        self.font_n = pygame.font.SysFont("dejavusans", 42, bold=True)
        self.reset()

    def reset(self):
        self.score = 0
        self.t = 0.0
        self.cx = self.cy = 0
        self.tx = self.ty = 0.0
        self.sparks = []
        self.ripples = []
        self.queue = []
        self.flags = 0
        self.cell = int((W - 2 * MARGIN_X) / COLS)
        self.ox = (W - self.cell * COLS) // 2
        self.oy = TOP
        cells = [(c, r) for r in range(ROWS) for c in range(COLS)]
        random.shuffle(cells)
        self.mine = set(cells[:MINES])
        self.adj = {}
        for c, r in cells:
            n = sum((c + dc, r + dr) in self.mine
                    for dc in (-1, 0, 1) for dr in (-1, 0, 1) if not (dc == dr == 0))
            self.adj[(c, r)] = n
        self.open = set()
        self.flag = set()
        self.safe = [p for p in cells if p not in self.mine]
        random.shuffle(self.safe)
        self.plan = list(self.safe)
        self.plan_i = 0
        self.cool = 0.0
        self.won = False

    def burst(self, x, y, col, n=12):
        for _ in range(n):
            a = random.uniform(0, 6.283)
            sp = random.uniform(60, 260)
            self.sparks.append({"x": x, "y": y, "vx": math.cos(a) * sp,
                                "vy": math.sin(a) * sp, "life": random.uniform(0.25, 0.7),
                                "col": col})

    def _flood(self, start):
        if start in self.open or start in self.flag or start in self.mine:
            return
        stack = [start]
        seen = set()
        while stack:
            p = stack.pop()
            if p in seen or p in self.mine or p in self.flag:
                continue
            seen.add(p)
            self.queue.append(p)
            if self.adj.get(p, 0) == 0:
                c, r = p
                for dc in (-1, 0, 1):
                    for dr in (-1, 0, 1):
                        q = (c + dc, r + dr)
                        if 0 <= q[0] < COLS and 0 <= q[1] < ROWS and q not in seen:
                            stack.append(q)

    def _center(self, c, r):
        return (self.ox + c * self.cell + self.cell // 2,
                self.oy + r * self.cell + self.cell // 2)

    def autoplay(self):
        self.cool -= 1.0 / FPS
        if self.queue or self.cool > 0:
            return
        if random.random() < 0.28:
            for p in list(self.open):
                if self.adj[p] == 0:
                    continue
                c, r = p
                hidden = []
                for dc in (-1, 0, 1):
                    for dr in (-1, 0, 1):
                        q = (c + dc, r + dr)
                        if 0 <= q[0] < COLS and 0 <= q[1] < ROWS and q not in self.open and q not in self.flag:
                            hidden.append(q)
                mines = [q for q in hidden if q in self.mine]
                if mines and len(hidden) == len(mines):
                    q = mines[0]
                    self.flag.add(q)
                    self.flags += 1
                    self.score += 40
                    self.cx, self.cy = q
                    x, y = self._center(*q)
                    self.burst(x, y, MAG, 10)
                    self.cool = 0.18
                    return
        while self.plan_i < len(self.plan):
            p = self.plan[self.plan_i]
            self.plan_i += 1
            if p in self.open or p in self.flag:
                continue
            self.cx, self.cy = p
            self._flood(p)
            self.cool = 0.12
            return
        self.won = True

    def update(self, dt):
        self.t += dt
        if self.record:
            self.autoplay()
        self.tx += (self.cx - self.tx) * min(1.0, dt * 10)
        self.ty += (self.cy - self.ty) * min(1.0, dt * 10)
        if self.queue:
            p = self.queue.pop(0)
            if p not in self.open and p not in self.mine:
                self.open.add(p)
                self.score += 12 + self.adj[p] * 4
                x, y = self._center(*p)
                col = NUMC.get(self.adj[p], TEAL)
                self.burst(x, y, col, 8 if self.adj[p] else 14)
                self.ripples.append({"x": x, "y": y, "r": 8, "life": 0.45, "col": col})
        for s in self.sparks:
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            s["life"] -= dt
        self.sparks = [s for s in self.sparks if s["life"] > 0]
        for r in self.ripples:
            r["r"] += 220 * dt
            r["life"] -= dt
        self.ripples = [r for r in self.ripples if r["life"] > 0]

    def handle(self, ev):
        if ev.type != pygame.KEYDOWN:
            return
        if ev.key in (pygame.K_a, pygame.K_LEFT):
            self.cx = max(0, self.cx - 1)
        elif ev.key in (pygame.K_d, pygame.K_RIGHT):
            self.cx = min(COLS - 1, self.cx + 1)
        elif ev.key in (pygame.K_w, pygame.K_UP):
            self.cy = max(0, self.cy - 1)
        elif ev.key in (pygame.K_s, pygame.K_DOWN):
            self.cy = min(ROWS - 1, self.cy + 1)
        elif ev.key in (pygame.K_SPACE, pygame.K_RETURN):
            self._flood((self.cx, self.cy))
        elif ev.key == pygame.K_f:
            p = (self.cx, self.cy)
            if p not in self.open:
                if p in self.flag:
                    self.flag.remove(p)
                    self.flags -= 1
                else:
                    self.flag.add(p)
                    self.flags += 1
                    self.score += 20
        elif ev.key == pygame.K_r:
            self.reset()

    def draw(self, s):
        s.fill(INK)
        for i in range(18):
            y = int((i * 130 + self.t * 40) % (H + 40)) - 20
            pygame.draw.line(s, PLUM, (0, y), (W, y), 2)
        pygame.draw.rect(s, COPPER, (self.ox - 14, self.oy - 14,
                                     self.cell * COLS + 28, self.cell * ROWS + 28), 3, border_radius=16)
        for r in range(ROWS):
            for c in range(COLS):
                x = self.ox + c * self.cell
                y = self.oy + r * self.cell
                pad = 6
                rec = pygame.Rect(x + pad, y + pad, self.cell - 2 * pad, self.cell - 2 * pad)
                p = (c, r)
                if p in self.open:
                    pygame.draw.rect(s, (22, 10, 36), rec, border_radius=10)
                    pygame.draw.rect(s, TEAL, rec, 2, border_radius=10)
                    n = self.adj[p]
                    if n:
                        glyph = self.font_n.render(str(n), True, NUMC.get(n, WHITE))
                        s.blit(glyph, glyph.get_rect(center=rec.center))
                    else:
                        pygame.draw.circle(s, (40, 80, 70), rec.center, 6)
                elif p in self.flag:
                    pygame.draw.rect(s, (48, 16, 40), rec, border_radius=10)
                    pygame.draw.rect(s, MAG, rec, 3, border_radius=10)
                    pygame.draw.polygon(s, MAG, [(rec.centerx - 8, rec.centery + 16),
                                                 (rec.centerx - 8, rec.centery - 16),
                                                 (rec.centerx + 16, rec.centery - 4)])
                    pygame.draw.line(s, GOLD, (rec.centerx - 8, rec.centery - 16),
                                     (rec.centerx - 8, rec.centery + 18), 3)
                else:
                    g = 18 + int(8 * math.sin(self.t * 2.4 + c * 0.7 + r * 0.5))
                    pygame.draw.rect(s, (48 + g, 18, 28 + g // 2), rec, border_radius=10)
                    pygame.draw.rect(s, COPPER, rec, 2, border_radius=10)
        ux = self.ox + self.tx * self.cell
        uy = self.oy + self.ty * self.cell
        cr = pygame.Rect(ux + 2, uy + 2, self.cell - 4, self.cell - 4)
        pygame.draw.rect(s, GOLD, cr, 4, border_radius=12)
        for rp in self.ripples:
            pygame.draw.circle(s, rp["col"], (int(rp["x"]), int(rp["y"])), int(rp["r"]), 2)
        for sp in self.sparks:
            pygame.draw.circle(s, sp["col"], (int(sp["x"]), int(sp["y"])), max(2, int(sp["life"] * 9)))
        title = self.font_lg.render(TITLE, True, COPPER)
        s.blit(title, title.get_rect(center=(W // 2, 62)))
        handle = self.font_sm.render(HANDLE, True, TEAL)
        s.blit(handle, handle.get_rect(center=(W // 2, 116)))
        meta = self.font_md.render(f"SCORE  {self.score}    FLAGS  {self.flags}/{MINES}", True, FOG)
        s.blit(meta, meta.get_rect(center=(W // 2, 176)))
        hint = self.font_sm.render("WASD move   SPACE open   F flag   R reset", True, MAG)
        s.blit(hint, hint.get_rect(center=(W // 2, H - 46)))
        if self.won:
            win = self.font_lg.render("FIELD CLEAR", True, GOLD)
            s.blit(win, win.get_rect(center=(W // 2, H - 90)))

    def play(self):
        run = True
        while run:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    run = False
                self.handle(ev)
            self.update(dt)
            self.draw(self.screen)
            pygame.display.flip()
        pygame.quit()

    def record_mp4(self, path):
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        frames = SECS * FPS
        surf = self.screen
        for _ in range(frames):
            self.update(1.0 / FPS)
            self.draw(surf)
            proc.stdin.write(pygame.image.tostring(surf, "RGB"))
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "ignore")
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1200:]}")
        print("wrote", path)
        pygame.quit()


def main():
    g = Game(record=RECORD)
    if PLAY and not RECORD:
        g.play()
    else:
        g.record_mp4(OUT)


if __name__ == "__main__":
    main()
