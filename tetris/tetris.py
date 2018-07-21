#!env python

import json
import pygame

ORIG_CELL_WIDTH = 80 # width of a cell on the resource image
CELL_WIDTH = 20
GRID_WIDTH = 10
GRID_HEIGHT = 22
GRID_HIDDEN = 2 # the top 2 rows are hidden
RATIO = ORIG_CELL_WIDTH / CELL_WIDTH
SCREEN_WIDTH = CELL_WIDTH * GRID_WIDTH
SCREEN_HEIGHT = CELL_WIDTH * (GRID_HEIGHT - GRID_HIDDEN)

FPS = 60

RESOURCES = "resources/" # TODO make it configurable
DESCRIPTORS = RESOURCES + "descriptors.json"
TETROMINOS = RESOURCES + "tetrominos.png"

BLACK = (0, 0, 0)

# TODO do a named tuple for pos and rects...

class Tetromino:
    def __init__(self, id):
        self.id = id
        self.pos = [3, 0] # position on the grid
        self.image = None
        self.last_update = 0
        self.level = 1

    def load(self, tetrominos, descriptors):
        desc = descriptors["tetrominos"][self.id]
        rect = tuple(desc[i] for i in ("x", "y", "w", "h"))
        w = rect[2] / RATIO
        h = rect[3] / RATIO
        self.image = tetrominos.subsurface(rect)
        self.image = pygame.transform.scale(self.image, (w, h))

    def update(self):
        ticks = pygame.time.get_ticks()
        if ticks - self.last_update >= (1 / self.level) * 1000:
            self.pos[1] += 1
            self.last_update = ticks

    def draw(self, screen):
        assert self.image is not None, "tetromino not loaded yet"
        x = self.pos[0] * CELL_WIDTH
        y = (self.pos[1] - GRID_HIDDEN) * CELL_WIDTH
        screen.blit(self.image, (x, y))

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    tetrominos = pygame.image.load(TETROMINOS)
    with open(DESCRIPTORS) as f:
        descriptors = json.load(f)

    clock = pygame.time.Clock()

    test = Tetromino(1)
    test.load(tetrominos, descriptors)

    running = True
    paused = False
    while running:
        screen.fill(BLACK)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        while paused:
            pass

        test.update()
        test.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()
