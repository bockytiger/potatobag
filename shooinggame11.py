# -*- coding: utf-8 -*-
"""
わり算シューティング（WebAssembly対応版）
pygame + pygbag 用
"""

import pygame
import random
import math
import sys
from collections import deque

pygame.init()

WIDTH, HEIGHT = 900, 650
# ★ Web対応：SCALED を追加
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
pygame.display.set_caption("わり算シューティング")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("meiryo", 22)
BIGFONT = pygame.font.SysFont("meiryo", 40)

TARGET_CORRECT = 20
FALL_SPEED_MIN = 60
FALL_SPEED_MAX = 140


def clamp(v, a, b):
    return max(a, min(b, v))


def make_spaceship_surface(size=80):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    w, h = size, size
    pygame.draw.polygon(
        s, (200, 30, 30),
        [(w*0.5, h*0.05), (w*0.9, h*0.6), (w*0.5, h*0.9), (w*0.1, h*0.6)]
    )
    pygame.draw.ellipse(s, (200, 220, 255), (w*0.35, h*0.25, w*0.3, h*0.2))
    pygame.draw.ellipse(s, (80, 120, 200), (w*0.37, h*0.28, w*0.26, h*0.14))
    pygame.draw.polygon(s, (255,160,0),
        [(w*0.45,h*0.85),(w*0.55,h*0.85),(w*0.5,h*1.05)]
    )
    return s


def make_meteor_surface(radius=36):
    size = radius * 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(s, (120, 80, 50), (radius, radius), radius)
    for _ in range(4):
        r = random.randint(6, radius//2)
        x = random.randint(radius//4, radius + radius//2)
        y = random.randint(radius//4, radius + radius//2)
        pygame.draw.circle(s, (90, 60, 40), (x, y), r)
    pygame.draw.circle(
        s, (180,130,80),
        (int(radius*0.6), int(radius*0.5)),
        int(radius*0.3), 1
    )
    return s


SPACESHIP_IMG = make_spaceship_surface(84)
METEOR_IMG = make_meteor_surface(38)


class ExplosionParticle:
    def __init__(self, pos):
        self.x, self.y = pos
        ang = random.random() * math.tau
        speed = random.uniform(80, 260)
        self.vx = math.cos(ang) * speed
        self.vy = math.sin(ang) * speed
        self.life = random.uniform(0.5, 1.0)
        self.age = 0
        self.size = random.uniform(2, 6)

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, surf):
        t = clamp(1 - self.age / self.life, 0, 1)
        if t <= 0:
            return
        alpha = int(255 * t)
        r = int(self.size * (1+t))
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255,180,50,alpha), (r, r), r)
        surf.blit(s, (self.x-r, self.y-r))


class Meteor:
    def __init__(self, x, y, text, speed):
        self.x = x
        self.y = y
        self.text = str(text)
        self.speed = speed
        self.surface = METEOR_IMG
        self.rect = self.surface.get_rect(center=(x, y))

    def update(self, dt):
        self.y += self.speed * dt
        self.rect.center = (self.x, self.y)

    def draw(self, surf):
        surf.blit(self.surface, self.rect.topleft)
        txt = FONT.render(self.text, True, (255,255,255))
        surf.blit(
            txt,
            (self.x - txt.get_width()//2, self.y - txt.get_height()//2)
        )


class QuestionGenerator:
    def __init__(self, difficulty):
        self.set_difficulty(difficulty)

    def set_difficulty(self, difficulty):
        self.difficulty = difficulty
        if difficulty == 0:
            self.divisors = list(range(1,6))
            self.max_dividend = 20
        elif difficulty == 1:
            self.divisors = list(range(6,10))
            self.max_dividend = 60
        else:
            self.divisors = list(range(1,10))
            self.max_dividend = 81

    def next_question(self):
        divisor = random.choice(self.divisors)
        quotient = random.randint(1, 9)
        return divisor * quotient, divisor, quotient


class Game:
    def __init__(self):
        self.state = "menu"
        self.difficulty = 0
        self.qgen = QuestionGenerator(self.difficulty)
        self.reset()

    def reset(self):
        self.correct = 0
        self.attempts = 0
        self.ship_x = WIDTH//2
        self.ship_y = HEIGHT - 80
        self.beam = None
        self.meteors = []
        self.particles = []
        self.make_question()

    def make_question(self):
        self.question = self.qgen.next_question()
        _, _, ans = self.question
        answers = {ans}
        while len(answers) < 4:
            answers.add(max(1, ans + random.randint(-3, 3)))
        answers = list(answers)
        random.shuffle(answers)

        self.meteors.clear()
        for i, a in enumerate(answers):
            x = 120 + i * 220
            y = random.randint(-200, -60)
            self.meteors.append(
                Meteor(x, y, a, random.uniform(FALL_SPEED_MIN, FALL_SPEED_MAX))
            )

    def fire(self):
        self.beam = [self.ship_x, self.ship_y - 30]

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.age < p.life]

        if self.state != "playing":
            return

        if self.beam:
            self.beam[1] -= 900 * dt
            if self.beam[1] < -20:
                self.beam = None

        for m in self.meteors:
            m.update(dt)

        if self.beam:
            br = pygame.Rect(self.beam[0]-3, self.beam[1]-10, 6, 20)
            for m in self.meteors:
                if m.rect.colliderect(br):
                    self.hit(m)
                    self.beam = None
                    break

    def hit(self, meteor):
        _, _, ans = self.question
        self.attempts += 1
        if int(meteor.text) == ans:
            self.correct += 1
            for _ in range(25):
                self.particles.append(
                    ExplosionParticle((meteor.x, meteor.y))
                )
        self.make_question()

    def draw(self, surf):
        surf.fill((10, 15, 40))

        if self.state == "menu":
            t = BIGFONT.render("わり算シューティング", True, (255,240,200))
            surf.blit(t, (WIDTH//2 - t.get_width()//2, 200))
            surf.blit(FONT.render("クリックでスタート", True, (220,220,220)),
                      (WIDTH//2 - 80, 280))
            return

        for m in self.meteors:
            m.draw(surf)

        if self.beam:
            pygame.draw.rect(surf, (255,220,80),
                             (self.beam[0]-3, self.beam[1]-14, 6, 28))

        surf.blit(
            SPACESHIP_IMG,
            SPACESHIP_IMG.get_rect(center=(self.ship_x, self.ship_y))
        )

        for p in self.particles:
            p.draw(surf)

        d, s, _ = self.question
        surf.blit(
            BIGFONT.render(f"{d} ÷ {s} = ?", True, (255,255,200)),
            (20, 20)
        )


game = Game()
pygame.mouse.set_visible(True)

running = True
while running:
    dt = clock.tick(60) / 1000

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEMOTION:
            if game.state == "playing":
                game.ship_x = clamp(event.pos[0], 40, WIDTH-40)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if game.state == "menu":
                game.state = "playing"
            else:
                game.fire()

    game.update(dt)
    game.draw(screen)
    pygame.display.flip()

pygame.quit()
