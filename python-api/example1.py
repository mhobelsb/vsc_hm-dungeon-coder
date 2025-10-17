from dungeoncoder import *
import time
def turn_right(hero: Hero):
    hero.turn_left()
    hero.turn_left()
    hero.turn_left()

# Initialize the game object
game = Game('../game/assets/levels/level1.json')
hero = game.get_hero()
hero.configure("Alarna the Mighty", 13)

# Move the hero
hero.turn_left()
hero.turn_left()
hero.turn_left()

hero.interact()

turn_right(hero)

for i in range(7):
    hero.move()

hero.turn_left()
hero.move()
hero.move()
turn_right(hero)
hero.move()

