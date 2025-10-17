from dungeoncoder import *

def turn_right(hero: Hero):
    hero.turn_left()
    hero.turn_left()
    hero.turn_left()

# Initialize the game object
game = Game()
hero = game.get_hero()
game.load_level('example_levels/level2.json')

def turn_right(hero):
    for _ in range(3):
        hero.turn_left()

hero.turn_left()
hero.turn_left()
for _ in range(8):
    hero.move()

turn_right(hero)
hero.move()
hero.move()
hero.move()
turn_right(hero)
for _ in range(8):
    hero.move()
hero.turn_left()
hero.move()
hero.move()
hero.move()
hero.turn_left()
for _ in range(9):
    hero.move()
