from dungeoncoder import Game, Hero

game = Game('../game/assets/levels/falling.json')
hero = game.get_hero()
hero.configure('Alibaba', 13)
hero.turn_left()
hero.turn_left()
hero.move()

