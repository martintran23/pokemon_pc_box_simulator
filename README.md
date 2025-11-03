# Pokémon PC Box Simulator

A Python application that mimics the **Pokémon PC storage system** from the games.
You can view your **party**, browse through **multiple PC boxes**, and inspect each Pokémon’s data.

---

## 🗂️ Project Structure
```
pokemon_pc/
│
├── main.py         # Entry point of the app (launches the GUI)
│
├── models/         # Data models for Pokémon, Boxes, and Player
│ ├── init.py
│ ├── pokemon.py    # Defines the Pokemon class
│ ├── box.py        # Defines the PCBox class
│ └── player.py     # Defines the Player class
│
├── data/
│ └── save.json     # Persistent save data for Pokémon
│
└── assets/
  └── bg/           # Backgrounds
  └── icons/
  └── sprites/
```

---

## Features

- Party display (up to 6 Pokémon)
- Multiple PC boxes (each can hold 30 Pokémon)
- View Pokémon data (name, level, type)
- Switch between boxes
- Easy to expand with sprites and save/load features