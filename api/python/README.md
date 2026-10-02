# dungeoncoder

The Python API for [Dungeon Coder](https://github.com/mhobelsb/vscode-dungeon-coder_v2), a VS Code extension in which a Python script steers a hero through a pixel-art dungeon.

```python
from dungeoncoder import Game

game = Game("playground.json")
hero = game.get_hero()
while not hero.is_at_goal():
    if hero.is_collision_in_front():
        hero.turn_left()
    else:
        hero.move()
```

- **With the extension:** start the game in VS Code (`Dungeon Coder: Start Game`); the script talks to it over a local REST API.
- **Without VS Code:** `dungeoncoder.use_simulator()` (or `DUNGEONCODER_SIM=1`) runs the same script in a pure-Python simulator of the game's rules: no picture, no waiting. `dungeoncoder.testing.spiel(map_text)` gives `(game, hero)` for pytest.
- **Levels from text maps:** `Game("karte.txt")`.

The package has the same version as the extension. Install it with `pip install dungeoncoder` (or from this repository: `pip install "git+https://github.com/mhobelsb/vscode-dungeon-coder_v2#subdirectory=api/python"`).
