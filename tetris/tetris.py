#!env python

import json
import numpy
import os
import pygame
import random

FPS = 60

BACKGROUND = (0, 0, 0)

ORIG_CELL_WIDTH = 80 # width of a cell on the resource image
CELL_WIDTH = 20
GRID_WIDTH = 10
GRID_HEIGHT = 22
GRID_HIDDEN = 2 # the top 2 rows are hidden
RATIO = ORIG_CELL_WIDTH / CELL_WIDTH
SCREEN_WIDTH = CELL_WIDTH * GRID_WIDTH
SCREEN_HEIGHT = CELL_WIDTH * (GRID_HEIGHT - GRID_HIDDEN)

RESOURCES = "resources/" # TODO make it configurable
DESCRIPTORS = RESOURCES + "descriptors.json"
TETROMINOS = RESOURCES + "tetrominos.png"

# TODO do a named tuple for pos and rects...

class Tetromino:
    def __init__(self, id):
        self.id = id
        self.pos = [3, 0] # position on the grid
        self.dim = []
        self.shape = None
        self.image = None
        self.last_update = 0
        self.level = 1
        self.falling = True
        self.done = False
        self.previous = None

    def load(self, tetrominos, descriptors):
        desc = descriptors["tetrominos"][self.id]
        rect = tuple(desc[i] for i in ("x", "y", "w", "h"))
        self.shape = numpy.array(desc["shape"], bool)
        self.shape = numpy.rot90(self.shape)

        w = rect[2] / RATIO
        h = rect[3] / RATIO
        self.image = tetrominos.subsurface(rect)
        self.image = pygame.transform.scale(self.image, (w, h))

        self.dim = [w / CELL_WIDTH, h / CELL_WIDTH]

    def rotate(self):
        self.image = pygame.transform.rotate(self.image, 90)
        self.dim[0], self.dim[1] = self.dim[1], self.dim[0]
        self.shape = numpy.rot90(self.shape)
        diff = self.pos[0] + self.dim[0] - GRID_WIDTH
        if diff > 0:
            self.pos[0] -= diff

    def revert(self):
        self.pos, self.dim, self.shape = self.previous

    def update(self, action):
        if self.done:
            return

        self.previous = list(self.pos), list(self.dim), numpy.array(self.shape)

        keys = pygame.key.get_pressed()
        ticks = pygame.time.get_ticks()
        rate = (1 / self.level) * 1000
        if keys[pygame.K_DOWN]:
            rate /= 10 # TODO make it configurable?
        if ticks - self.last_update >= rate:
            if self.falling:
                self.pos[1] += 1
            else:
                self.done = True
                return
            self.last_update = ticks

        if action == "right":
            self.pos[0] += 1
        elif action == "left":
            self.pos[0] -= 1
        elif action == "rotate":
            self.rotate()

    def draw(self, screen):
        assert self.image, "tetromino not loaded yet"
        x = self.pos[0] * CELL_WIDTH
        y = (self.pos[1] - GRID_HIDDEN) * CELL_WIDTH
        screen.blit(self.image, (x, y))

class Grid:
    def __init__(self, image, descriptors):
        self.image = image
        self.descriptors = descriptors
        self.grid = numpy.zeros((GRID_WIDTH, GRID_HEIGHT), dtype=bool)
        self.orig = None
        self.tetrominos = []
        self.current = None
        self.next = Tetromino(random.randint(0, 6)) # TODO display it

    def clear_previous(self):
        if self.current.previous is not None:
            x, y = self.current.previous[0]
            w, h = self.current.previous[1]
            shape = self.current.previous[2]
            for i in range(w):
                for j in range(h):
                    if shape[i][j]:
                        if self.orig is None or not self.orig[x + i][y + j]:
                            self.grid[x + i][y + j] = False

    def update_grid(self):
        x, y = self.current.pos
        w, h = self.current.dim
        shape = self.current.shape
        for i in range(w):
            for j in range(h):
                if shape[i][j]:
                    self.grid[x + i][y + j] = True
        for i in range(GRID_HEIGHT):
            if all(cell for cell in self.grid[:,i]):
                print "tetris row " + str(i)

    def print_grid(self, grid=None):
        if grid is None:
            grid = self.grid
        assert len(grid), "grid not initialized yet"

        for i in range(len(grid)):
            row = ""
            for j in range(len(grid[i])):
                row += '*' if grid[i][j] else ' '
            print row

    def bump(self):
        x, y = self.current.pos
        w, h = self.current.dim
        shape = self.current.shape

        # collisions with walls and ground
        if x < 0:
            return True
        if x + w > GRID_WIDTH:
            return True
        if y + h > GRID_HEIGHT:
            self.current.falling = False
            return True

        # collisions with other tetrominos
        for i in range(w):
            for j in range(h):
                if shape[i][j] and self.orig[x + i][y + j]:
                    if self.current.previous[0][1] < y:
                        self.current.falling = False
                    return True

        return False

    def update(self, action):
        if self.current is None or self.current.done:
            if not self.current is None:
                self.tetrominos.append(self.current)
            self.current = self.next
            self.current.load(self.image, self.descriptors)
            self.next = Tetromino(random.randint(0, 6))
            self.orig = numpy.array(self.grid)

        self.current.update(action)
        self.clear_previous()
        if self.bump():
            self.current.revert()
        self.update_grid()

    def draw(self, screen):
        assert self.current, "tetromino not loaded yet"
        self.current.draw(screen)
        for tetromino in self.tetrominos:
            tetromino.draw(screen)

if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption("Tetris")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    tetrominos = pygame.image.load(TETROMINOS)
    with open(DESCRIPTORS) as f:
        descriptors = json.load(f)

    grid = Grid(tetrominos, descriptors)

    running = True
    paused = False
    while running:
        screen.fill(BACKGROUND)

        action = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = not paused
                    grid.print_grid()
                elif event.key == pygame.K_RIGHT:
                    action = "right"
                elif event.key == pygame.K_LEFT:
                    action = "left"
                elif event.key == pygame.K_SPACE or \
                     event.key == pygame.K_UP:
                    action = "rotate"

        if paused:
            continue

        grid.update(action)
        grid.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
