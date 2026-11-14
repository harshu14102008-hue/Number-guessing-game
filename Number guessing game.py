"""Guess The Number - graphical version (Python + Pygame).

The computer picks a secret number. Use the on-screen keypad (mouse/touch) or your
keyboard to guess. A thermometer shows how close you are and a range bar shows
where the secret number can still be.

Keyboard: 0-9 type, Backspace clear, Enter submit, 1/2/3 pick level, R restart, Esc quit.
"""
import json
import math
import random
import sys

import pygame

W, H = 480, 720
LEVELS = [("Easy", 50, 8), ("Medium", 100, 7), ("Hard", 500, 9)]
HS_FILE = "guess_gui_highscore.json"

BG, PANEL, TEXT = (22, 24, 38), (38, 42, 66), (235, 235, 245)
ACCENT, GOOD, BAD, GOLD = (90, 140, 255), (80, 210, 130), (255, 90, 90), (255, 205, 70)
KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "GO"]


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def load_scores():
    try:
        with open(HS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


class Game:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.scores = load_scores()
        self.pressed = None          # (label, frames_left)
        self.particles = []
        self.tick = 0
        self.menu()

    # ---------- state changes ----------
    def menu(self):
        self.state = "menu"

    def start(self, idx):
        self.name, self.high, self.max_tries = LEVELS[idx]
        self.secret = self.rng.randint(1, self.high)
        self.tries, self.text = 0, ""
        self.lo, self.hi = 1, self.high
        self.last, self.heat, self.shown_heat = None, 0.0, 0.0
        self.msg, self.msg_color, self.direction = "Make your first guess!", TEXT, 0
        self.shake, self.score, self.state = 0, 0, "play"
        self.won = False

    def submit(self):
        if not self.text or not (1 <= int(self.text) <= self.high):
            self.msg, self.msg_color, self.direction = f"Enter a number 1 - {self.high}", BAD, 0
            self.shake, self.text = 12, ""
            return
        g = int(self.text)
        self.text, self.tries, self.last = "", self.tries + 1, g
        if g == self.secret:
            self.won, self.state = True, "end"
            self.score = (self.max_tries - self.tries + 1) * 10
            if self.score > self.scores.get(self.name, 0):
                self.scores[self.name] = self.score
                try:
                    json.dump(self.scores, open(HS_FILE, "w"))
                except OSError:
                    pass
            self.heat = 1.0
            self.particles = [[W / 2, 250, self.rng.uniform(-5, 5), self.rng.uniform(-11, -2),
                               self.rng.choice([GOLD, GOOD, ACCENT, BAD])] for _ in range(140)]
            return
        self.heat = max(0.0, 1 - abs(g - self.secret) / (self.high * 0.5))
        if g < self.secret:
            self.lo, self.direction = max(self.lo, g + 1), 1
            self.msg, self.msg_color = "Too low - go higher!", ACCENT
        else:
            self.hi, self.direction = min(self.hi, g - 1), -1
            self.msg, self.msg_color = "Too high - go lower!", GOLD
        self.shake = 8
        if self.tries >= self.max_tries:
            self.won, self.state = False, "end"

    # ---------- input ----------
    def buttons(self):
        b = []
        if self.state == "menu":
            for i, (n, h, t) in enumerate(LEVELS):
                b.append((f"L{i}", pygame.Rect(60, 260 + i * 110, 360, 88), f"{n}   (1-{h}, {t} tries)"))
        elif self.state == "play":
            for i, k in enumerate(KEYS):
                r = pygame.Rect(40 + (i % 3) * 140, 442 + (i // 3) * 66, 120, 56)
                b.append((k, r, "OK" if k == "GO" else k))
        else:
            b.append(("AGAIN", pygame.Rect(60, 500, 360, 70), "Play again"))
            b.append(("MENU", pygame.Rect(60, 590, 360, 70), "Change level"))
        return b

    def tap(self, label):
        self.pressed = (label, 6)
        if label.startswith("L") and len(label) == 2:
            self.start(int(label[1]))
        elif label == "AGAIN":
            self.start(LEVELS.index(next(l for l in LEVELS if l[0] == self.name)))
        elif label == "MENU":
            self.menu()
        elif label == "C":
            self.text = self.text[:-1]
        elif label == "GO":
            self.submit()
        elif label.isdigit() and len(self.text) < len(str(self.high)):
            self.text += label

    def click(self, pos):
        for label, rect, _ in self.buttons():
            if rect.collidepoint(pos):
                self.tap(label)
                return

    def key(self, k, ch):
        if self.state == "menu" and ch in "123":
            self.tap("L" + str(int(ch) - 1))
        elif self.state == "play":
            if ch.isdigit():
                self.tap(ch)
            elif k == pygame.K_BACKSPACE:
                self.tap("C")
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.tap("GO")
        elif self.state == "end" and ch in ("r", "R"):
            self.tap("AGAIN")

    def update(self):
        self.tick += 1
        if self.pressed:
            self.pressed = (self.pressed[0], self.pressed[1] - 1) if self.pressed[1] > 1 else None
        if self.state != "menu":
            self.shown_heat += (self.heat - self.shown_heat) * 0.15
            self.shake = max(0, self.shake - 1)
        for p in self.particles:
            p[0] += p[2]; p[1] += p[3]; p[3] += 0.35
        self.particles = [p for p in self.particles if p[1] < H + 20]

    # ---------- drawing ----------
    def text_at(self, s, font, color, cx, y):
        t = font.render(s, True, color)
        self.surf.blit(t, (cx - t.get_width() / 2, y))

    def draw(self, surf, fonts):
        self.surf = surf
        f_s, f_m, f_l, f_xl = fonts
        surf.fill(BG)
        self.text_at("GUESS THE NUMBER", f_l, TEXT, W / 2, 22)
        if self.state == "menu":
            self.text_at("Pick a level to start", f_m, (170, 175, 205), W / 2, 150)
            self.text_at("Can you find the secret number?", f_s, (130, 135, 170), W / 2, 190)
        else:
            self.draw_play(f_s, f_m, f_l, f_xl)
        for label, rect, txt in self.buttons():
            down = self.pressed and self.pressed[0] == label
            col = ACCENT if label == "GO" or self.state != "play" else PANEL
            if label == "C":
                col = (110, 60, 70)
            if down:
                col = lerp(col, (255, 255, 255), 0.35)
            r = rect.move(0, 3 if down else 0)
            pygame.draw.rect(surf, lerp(col, (0, 0, 0), 0.35), rect.move(0, 4), border_radius=14)
            pygame.draw.rect(surf, col, r, border_radius=14)
            self.text_at(txt, f_m if len(txt) > 3 else f_l, TEXT, r.centerx, r.centery - (18 if len(txt) <= 3 else 14))
        for x, y, _, _, c in self.particles:
            pygame.draw.rect(surf, c, (int(x), int(y), 7, 7))

    def draw_play(self, f_s, f_m, f_l, f_xl):
        s = self.surf
        self.text_at(f"{self.name}  |  1 - {self.high}", f_s, (150, 155, 190), W / 2, 70)
        for i in range(self.max_tries):            # attempts as dots
            c = (60, 64, 90) if i < self.tries else GOOD
            pygame.draw.circle(s, c, (int(W / 2 + (i - (self.max_tries - 1) / 2) * 34), 112), 11)
        # range bar
        x0, x1, y = 40, 440, 160
        pygame.draw.rect(s, PANEL, (x0, y, x1 - x0, 14), border_radius=7)
        a = x0 + (self.lo - 1) / self.high * (x1 - x0)
        b = x0 + self.hi / self.high * (x1 - x0)
        pygame.draw.rect(s, GOOD, (a, y, max(6, b - a), 14), border_radius=7)
        self.text_at(f"Secret is between {self.lo} and {self.hi}", f_s, (150, 155, 190), W / 2, 182)
        # hint panel
        off = int(math.sin(self.tick * 1.8) * self.shake)
        pygame.draw.rect(s, PANEL, (40 + off, 215, 400, 110), border_radius=16)
        shown = self.msg
        if self.state == "end":
            shown = "YOU WON!" if self.won else f"Out of tries! It was {self.secret}"
            self.msg_color = GOLD if self.won else BAD
        self.text_at(shown, f_m, self.msg_color, W / 2 + off, 222)
        if self.state == "end" and self.won:
            self.text_at(f"{self.secret}  in {self.tries} tries", f_l, TEXT, W / 2, 255)
            self.text_at(f"Score {self.score}   Best {self.scores.get(self.name, 0)}", f_s, GOLD, W / 2, 298)
        elif self.last is not None:
            cx, cy = 90 + off, 285
            if self.direction:
                pts = [(cx, cy - 22), (cx - 20, cy + 14), (cx + 20, cy + 14)] if self.direction > 0 else \
                      [(cx, cy + 22), (cx - 20, cy - 14), (cx + 20, cy - 14)]
                pygame.draw.polygon(s, self.msg_color, pts)
            self.text_at(f"Last guess: {self.last}", f_m, TEXT, W / 2 + 30 + off, 268)
        # thermometer
        pygame.draw.rect(s, PANEL, (40, 337, 400, 22), border_radius=11)
        w = max(14, 400 * self.shown_heat)
        pygame.draw.rect(s, lerp((60, 140, 255), (255, 70, 60), self.shown_heat), (40, 337, w, 22), border_radius=11)
        self.text_at("COLD", f_s, (110, 160, 255), 70, 361)
        self.text_at("HOT", f_s, (255, 110, 100), 412, 361)
        if self.state == "play":
            self.draw_input(f_l)

    def draw_input(self, f_l):
        box = pygame.Rect(140, 388, 200, 46)
        pygame.draw.rect(self.surf, (12, 13, 22), box, border_radius=10)
        pygame.draw.rect(self.surf, ACCENT, box, 2, border_radius=10)
        cursor = "_" if (self.tick // 20) % 2 == 0 else " "
        self.text_at(self.text + cursor, f_l, TEXT, box.centerx, box.y + 2)


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Guess The Number")
    fonts = [pygame.font.SysFont("arial", n, True) for n in (18, 26, 36, 56)]
    clock, g = pygame.time.Clock(), Game()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN:
                g.click(e.pos)
            if e.type == pygame.KEYDOWN:
                g.key(e.key, e.unicode)
        g.update()
        g.draw(screen, fonts)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
