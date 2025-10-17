from dungeoncoder import *

def turn_north(hero: Hero):
    while(not hero.is_facing_north()):
        hero.turn_left()

def move_until_wall(hero: Hero):
    while(not hero.is_collision_in_front()):
        hero.move()

def turn_right(hero: Hero):
    hero.turn_left()
    hero.turn_left()
    hero.turn_left()

# Initialize the game object
game = Game('../game/assets/levels/level1.json')
hero = game.get_hero()
hero.configure("Alarna the Mighty", 13)


turn_north(hero)
move_until_wall(hero)
print(hero.is_torch_in_front())

