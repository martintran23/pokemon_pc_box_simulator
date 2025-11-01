import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
import json, os

from models.pokemon import Pokemon
from models.box import PCBox
from models.player import Player

SAVE_PATH = "data/save.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class PCApp(tk.Tk):
    def __init__(self, player):
        super().__init__()
        self.title("Pokémon PC Box System")
        self.geometry("850x600")
        self.resizable(False, False)

        self.player = player

        # --- Load images ---
        bg_path = os.path.join(BASE_DIR, "assets", "bg", "box_bg.png")
        bg_raw = Image.open(bg_path).resize((650, 550))
        self.bg_image = ImageTk.PhotoImage(bg_raw)

        add_icon_path = os.path.join(BASE_DIR, "assets", "icons", "add_icon.png")
        self.add_icon = ImageTk.PhotoImage(Image.open(add_icon_path).resize((60, 60)))

        # Sprite cache
        self.sprite_cache = {}

        self.create_widgets()
        self.load_game()
        self.update_display()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------- Widgets ----------------
    def create_widgets(self):
        # Left: Party
        self.party_frame = tk.Frame(self, bg="#f0f0f0", width=200)
        self.party_frame.pack(side="left", fill="y")

        tk.Label(
            self.party_frame, text="Your Party", font=("Arial", 14, "bold"), bg="#f0f0f0"
        ).pack(pady=10)

        self.party_labels = []
        for i in range(6):
            lbl = tk.Button(
                self.party_frame,
                text="(empty)",
                width=80,
                height=80,
                command=lambda i=i: self.show_pokemon("party", i),
            )
            lbl.pack(pady=5)
            self.party_labels.append(lbl)

        # Right: PC Box Area
        self.pc_area = tk.Frame(self, bg="#ff9b9b")
        self.pc_area.pack(side="right", expand=True, fill="both")

        self.box_frame = tk.Frame(self.pc_area, bg="#ff9b9b", padx=20, pady=20)
        self.box_frame.pack(expand=True)

        self.box_canvas = tk.Canvas(
            self.box_frame, width=650, height=550, highlightthickness=0, bg="#ffffff"
        )
        self.box_canvas.pack()
        self.box_canvas.create_image(0, 0, anchor="nw", image=self.bg_image)

        # 30 slot buttons
        self.slot_buttons = []
        start_x, start_y = 60, 60
        gap_x, gap_y = 90, 85
        for i in range(30):
            x = start_x + (i % 6) * gap_x
            y = start_y + (i // 6) * gap_y
            btn = tk.Button(
                self.box_canvas,
                image=self.add_icon,
                borderwidth=0,
                command=lambda i=i: self.toggle_pokemon_slot(i),
            )
            self.box_canvas.create_window(x, y, anchor="nw", window=btn)
            self.slot_buttons.append(btn)

        # Navigation buttons
        nav_frame = tk.Frame(self.box_frame, bg="#ff9b9b")
        nav_frame.pack(pady=10)
        tk.Button(nav_frame, text="< Prev", command=self.prev_box).grid(row=0, column=0, padx=10)
        self.box_name_lbl = tk.Label(nav_frame, text="", bg="#ff9b9b", font=("Arial", 12, "bold"))
        self.box_name_lbl.grid(row=0, column=1)
        tk.Button(nav_frame, text="Next >", command=self.next_box).grid(row=0, column=2, padx=10)

    # ---------------- Save/Load ----------------
    def save_game(self):
        data = {
            "party": [mon.__dict__ if mon else None for mon in self.player.party],
            "boxes": [
                [mon.__dict__ if mon else None for mon in box.pokemon]
                for box in self.player.boxes
            ],
            "current_box": self.player.current_box,
        }
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        with open(SAVE_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def load_game(self):
        if not os.path.exists(SAVE_PATH):
            return
        try:
            with open(SAVE_PATH, "r") as f:
                content = f.read().strip()
                if not content:
                    print("⚠️ Empty save file, starting fresh.")
                    return
                data = json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️ Failed to load save: {e}")
            return

        self.player.party = [
            Pokemon(**mon) if mon else None for mon in data.get("party", [])
        ]

        for i, box_data in enumerate(data.get("boxes", [])):
            if i < len(self.player.boxes):
                self.player.boxes[i].pokemon = [
                    Pokemon(**mon) if mon else None for mon in box_data
                ]

        self.player.current_box = data.get("current_box", 0)

    def on_close(self):
        self.save_game()
        self.destroy()

    # ---------------- Sprite Loader ----------------
    def get_sprite(self, pokemon):
        if not pokemon:
            return self.add_icon

        if pokemon.name in self.sprite_cache:
            return self.sprite_cache[pokemon.name]

        try:
            img_path = os.path.join(BASE_DIR, pokemon.sprite)
            if not os.path.exists(img_path):
                print(f"⚠️ Sprite not found for {pokemon.name}: {img_path}")
                return self.add_icon

            img_raw = Image.open(img_path).convert("RGBA")
            img_raw = img_raw.resize((60, 60), Image.Resampling.LANCZOS)
            img = ImageTk.PhotoImage(img_raw)
            self.sprite_cache[pokemon.name] = img
            return img
        except Exception as e:
            print(f"⚠️ Failed to load sprite for {pokemon.name}: {e}")
            return self.add_icon

    # ---------------- Update Display ----------------
    def update_display(self):
        # Party
        for i, mon in enumerate(self.player.party):
            sprite_img = self.get_sprite(mon)
            self.party_labels[i].image = sprite_img
            self.party_labels[i].config(text="", image=sprite_img)

        # Box
        box = self.player.get_current_box()
        self.box_name_lbl.config(text=box.name)
        for i, mon in enumerate(box.pokemon):
            sprite_img = self.get_sprite(mon)
            self.slot_buttons[i].image = sprite_img
            self.slot_buttons[i].config(
                text="",
                image=sprite_img,
                width=60,
                height=60,
                command=lambda i=i: self.remove_pokemon(i) if box.pokemon[i] else self.add_pokemon(i),
            )

    # ---------------- Pokémon Actions ----------------
    def add_pokemon(self, index):
        name = simpledialog.askstring("Add Pokémon", "Enter Pokémon name:")
        if not name:
            return
        level = simpledialog.askinteger("Level", "Enter level:", minvalue=1, maxvalue=100)
        ptype = simpledialog.askstring("Type", "Enter type:")
        sprite_filename = simpledialog.askstring(
            "Sprite Filename",
            "Optional: enter sprite filename (e.g., bulbasaur.png):"
        )
        if name and level and ptype:
            sprite_path = os.path.join(BASE_DIR, "assets", "sprites", sprite_filename) if sprite_filename else os.path.join(BASE_DIR, "assets", "sprites", f"{name.lower()}.png")
            new_mon = Pokemon(name, level, ptype, sprite=sprite_path)
            self.player.get_current_box().add_pokemon(new_mon, index)
            self.update_display()
            self.save_game()

    def remove_pokemon(self, index):
        box = self.player.get_current_box()
        mon = box.pokemon[index]
        if not mon:
            return
        confirm = messagebox.askyesno("Remove Pokémon", f"Release {mon.name}?")
        if confirm:
            box.remove_pokemon(index)
            self.update_display()
            self.save_game()

    def show_pokemon(self, area, index):
        if area == "party":
            mon = self.player.party[index]
            if mon:
                messagebox.showinfo("Pokémon Info", mon.summary())
            else:
                messagebox.showinfo("Empty Slot", "No Pokémon here!")

    # ---------------- Box Navigation ----------------
    def next_box(self):
        self.player.current_box = (self.player.current_box + 1) % len(self.player.boxes)
        self.update_display()
        self.save_game()

    def prev_box(self):
        self.player.current_box = (self.player.current_box - 1) % len(self.player.boxes)
        self.update_display()
        self.save_game()

    def toggle_pokemon_slot(self, index):
        box = self.player.get_current_box()
        if box.pokemon[index]:
            self.remove_pokemon(index)
        else:
            self.add_pokemon(index)


# --- MAIN ---
if __name__ == "__main__":
    player = Player()
    app = PCApp(player)
    app.mainloop()
