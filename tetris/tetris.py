#!env python

import json
import numpy
import os
import pygame
import random

FPS = 60
SECOND = 1000 # ms

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GREY = (100, 100, 100)

ORIG_CELL_WIDTH = 80 # width of a cell on the resource image
CELL_WIDTH = 20
GRID_WIDTH = 10
GRID_HEIGHT = 22
GRID_HIDDEN = 2 # the top 2 rows are hidden
RATIO = ORIG_CELL_WIDTH / CELL_WIDTH
SCREEN_WIDTH = CELL_WIDTH * GRID_WIDTH
MARGIN = 6 * CELL_WIDTH
TOTAL_SCREEN_WIDTH = SCREEN_WIDTH + MARGIN
SCREEN_HEIGHT = CELL_WIDTH * (GRID_HEIGHT - GRID_HIDDEN)

RESOURCES = "resources/" # TODO make it configurable
DESCRIPTORS = RESOURCES + "descriptors.json"
TETROMINOS = RESOURCES + "tetrominos.png"

class Text:
    def __init__(self, text, color=WHITE):
        self.text = text
        self.font = pygame.font.SysFont("Comic Sans MS", CELL_WIDTH)
        self.color = color
        self.label = self.font.render(text, 1, self.color)
        rect = self.label.get_rect()
        self.dim = (rect.width, rect.height)
        x = (SCREEN_WIDTH - self.label.get_rect().width) / 2
        y = (SCREEN_HEIGHT - self.label.get_rect().height) / 2
        self.pos = [x, y]

    def draw(self, screen):
        self.label = self.font.render(self.text, 1, self.color)
        screen.blit(self.label, self.pos)

class Menu:
    def __init__(self, title, choices):
        self.title = Text(title)
        self.choices = [Text(choice) for choice in choices]
        self.current = 0
        self.choice = None
        height = self.title.dim[1] + 40 + sum(choice.dim[1] + 20 for choice in self.choices) - 20
        self.title.pos[1] = (SCREEN_HEIGHT - height) / 2
        i = 0
        for choice in self.choices:
            choice.pos[1] = self.title.pos[1] + self.title.dim[1] + 40 + (i * (choice.dim[1] + 20))
            i += 1

    def update(self, action):
        self.choices[self.current].color = RED
        if action == "up":
            self.current = len(self.choices) - 1 if self.current == 0 else self.current - 1
        elif action == "down":
            self.current = 0 if self.current == len(self.choices) - 1 else self.current + 1
        elif action == "ok":
            self.choices[self.current].color = BLUE
            self.choice = self.choices[self.current].text

    def draw(self, screen):
        self.title.draw(screen)
        i = 0
        for choice in self.choices:
            if i != self.current:
                choice.color = WHITE
            choice.draw(screen)
            i += 1

class Tetromino:
    def __init__(self, id, level):
        self.id = id
        self.pos = [3, 0] # position on the grid
        self.dim = []
        self.shape = None
        self.color = ""
        self.last_update = 0
        self.level = level
        self.falling = True
        self.done = False
        self.previous = None
        self.rate = SECOND
        for i in range(self.level):
            self.rate -= self.rate / 3

    def load(self, tetrominos, descriptors):
        desc = descriptors["tetrominos"][self.id]
        rect = tuple(desc[i] for i in ("x", "y", "w", "h"))
        self.shape = numpy.array(desc["shape"], bool)
        self.shape = numpy.rot90(self.shape)
        self.color = desc["color"]

        w = rect[2] / RATIO
        h = rect[3] / RATIO

        self.dim = [w / CELL_WIDTH, h / CELL_WIDTH]

    def rotate(self):
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
        rate = self.rate
        if keys[pygame.K_DOWN]:
            rate /= 10
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

    def draw(self, screen, pos, color):
        for i in range(self.dim[0]):
            for j in range(self.dim[1]):
                if self.shape[i][j]:
                    x = pos[0] + i * CELL_WIDTH
                    y = pos[1] + j * CELL_WIDTH
                    screen.blit(color, (x, y))

class Grid:
    def __init__(self, image, descriptors):
        self.running = True
        self.image = image
        self.descriptors = descriptors
        self.grid = numpy.empty((GRID_WIDTH, GRID_HEIGHT), dtype=object)
        self.orig = None
        self.current = None
        self.last_update = 0
        self.lines = { 1: (Text("SINGLE"), 40, 1),
                       2: (Text("DOUBLE"), 100, 3),
                       3: (Text("TRIPLE"), 300, 5),
                       4: (Text("TETRIS", color=GREEN), 1200, 8),
                       5: (Text("CLEAR", color=GREEN), 2000, 10) }
        self.rows = 0
        self.score = 0
        self.level = 0
        self.count = 0
        self.goal = 5 * (self.level + 1)
        self.next = Tetromino(random.randint(0, 6), self.level)
        self.next.load(self.image, self.descriptors)
        self.colors = {}
        for desc in self.descriptors["tetrominos"]:
            # In the descriptors, x and y represent the position
            # in the image of a square of the tetromino's color.
            rect = (desc["x"], desc["y"], CELL_WIDTH, CELL_WIDTH)
            image = self.image.subsurface(rect)
            image = pygame.transform.scale(image, (CELL_WIDTH, CELL_WIDTH))
            self.colors[desc["color"]] = image

    def clear_previous(self):
        if self.current.previous is not None:
            x, y = self.current.previous[0]
            w, h = self.current.previous[1]
            shape = self.current.previous[2]
            for i in range(w):
                for j in range(h):
                    if shape[i][j]:
                        if self.orig is None or not self.orig[x + i][y + j]:
                            self.grid[x + i][y + j] = None

    def tetris(self):
        rows = 0
        i = GRID_HEIGHT - 1
        cleared = True
        while i >= 0:
            if all(cell for cell in self.grid[:,i]):
                for j in range(i + 1)[::-1][:-1]:
                    self.grid[:,j] = self.grid[:,j - 1]
                rows += 1
                i += 1
            elif any(cell is not None for cell in self.grid[:,i]):
                cleared = False
            i -= 1
        if cleared:
            rows = 5
        if rows in self.lines:
            self.rows = rows
            self.score += self.lines[rows][1] * (self.level + 1)
            self.score += rows * GRID_WIDTH # FIXME really?
            self.count += self.lines[rows][2]
            if self.count >= self.goal:
                self.level += 1
                self.goal = 5 * (self.level + 1)
                self.count = 0
            self.last_update = pygame.time.get_ticks()

    def update_grid(self):
        x, y = self.current.pos
        w, h = self.current.dim
        shape = self.current.shape
        color = self.current.color
        for i in range(w):
            for j in range(h):
                if shape[i][j]:
                    self.grid[x + i][y + j] = color
        if self.current.done:
            self.tetris()

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
            self.current = self.next
            self.next = Tetromino(random.randint(0, 6), self.level)
            self.next.load(self.image, self.descriptors)
            self.orig = numpy.array(self.grid)
            if any(cell for cell in self.orig[:,0]):
                self.running = False # game over

        self.current.update(action)
        self.clear_previous()
        if self.bump():
            self.current.revert()
        self.update_grid()

    def draw(self, screen):
        for i in range(GRID_WIDTH):
            for j in range(GRID_HEIGHT)[2:]:
                color = self.grid[i][j]
                if color is not None:
                    pos = (i * CELL_WIDTH, (j - 2) * CELL_WIDTH)
                    screen.blit(self.colors[color], pos)
        if self.rows in self.lines:
            self.lines[self.rows][0].draw(screen)
            ticks = pygame.time.get_ticks()
            if ticks - self.last_update >= SECOND:
                self.rows = 0
                self.last_update = ticks

class Margin:
    def __init__(self):
        self.next = None
        self.rect = (SCREEN_WIDTH, 0, MARGIN, SCREEN_HEIGHT)
        x = SCREEN_WIDTH + CELL_WIDTH
        self.score_title = Text("SCORE", color=BLACK)
        h = self.score_title.dim[1]
        self.score_title.pos = (x, CELL_WIDTH)
        self.score = Text(str(0))
        self.score.pos = (x, self.score_title.pos[1] + h + CELL_WIDTH)
        self.level_title = Text("LEVEL", color=BLACK)
        self.level_title.pos = (x, self.score.pos[1] + h + 2 * CELL_WIDTH)
        self.level = Text(str(0))
        self.level.pos = (x, self.level_title.pos[1] + h + CELL_WIDTH)
        self.next_title = Text("NEXT", color=BLACK)
        self.next_title.pos = (x, self.level.pos[1] + h + 2 * CELL_WIDTH)
        self.next_pos = [x, self.next_title.pos[1] + h + CELL_WIDTH]

    def update(self, next, score, level):
        self.next = next
        self.score.text = str(score)
        self.level.text = str(level)

    def draw(self, screen, colors):
        self.margin = screen.subsurface(self.rect)
        self.margin.fill(GREY)
        self.score_title.draw(screen)
        self.score.draw(screen)
        self.level_title.draw(screen)
        self.level.draw(screen)
        self.next_title.draw(screen)
        if self.next:
            self.next.draw(screen, self.next_pos, colors[self.next.color])

if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption("Tetris")
    screen = pygame.display.set_mode((TOTAL_SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    tetrominos = pygame.image.load(TETROMINOS)
    with open(DESCRIPTORS) as f:
        descriptors = json.load(f)

    grid = Grid(tetrominos, descriptors)
    margin = Margin()
    pause = Menu("PAUSE", ["RESUME", "NEW GAME", "QUIT"])
    gameover = Menu("GAME ORVER", ["NEW GAME", "QUIT"])

    paused = False
    running = True
    while running:
        screen.fill(BLACK)

        action = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = not paused
                elif event.key == pygame.K_RIGHT:
                    action = "right"
                elif event.key == pygame.K_LEFT:
                    action = "left"
                elif not paused and grid.running and \
                        ( event.key == pygame.K_SPACE or
                          event.key == pygame.K_UP ):
                    action = "rotate"
                elif event.key == pygame.K_UP:
                    action = "up"
                elif event.key == pygame.K_DOWN:
                    action = "down"
                elif event.key == pygame.K_SPACE or \
                     event.key == pygame.K_RETURN:
                    action = "ok"

        grid.draw(screen)

        if not grid.running:
            gameover.update(action)
            gameover.draw(screen)
            if gameover.choice == "NEW GAME":
                grid = Grid(tetrominos, descriptors)
                margin = Margin()
            elif gameover.choice == "QUIT":
                running = False
            gameover.choice = None
        elif paused:
            pause.update(action)
            pause.draw(screen)
            paused = not paused
            if pause.choice == "NEW GAME":
                grid = Grid(tetrominos, descriptors)
                margin = Margin()
            elif pause.choice == "QUIT":
                running = False
            elif pause.choice != "RESUME":
                paused = not paused
            pause.choice = None
        else:
            grid.update(action)

        margin.update(grid.next, grid.score, grid.level)
        margin.draw(screen, grid.colors)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
