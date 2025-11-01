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
        self.drag_data = {"pokemon": None, "origin_index": None, "origin_area": None, "floating": None}

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
            lbl = tk.Label(
                self.party_frame,
                text="(empty)",
                width=80,
                height=80,
                bd=2,
                relief="raised",
                bg="#ffffff",
            )
            lbl.pack(pady=5)
            lbl.bind("<Button-1>", lambda e, i=i: self.start_drag(e, "party", i))
            lbl.bind("<ButtonRelease-1>", self.end_drag)
            lbl.bind("<Button-3>", lambda e, i=i: self.right_click("party", i))
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
        self.slot_positions = []
        start_x, start_y = 60, 60
        gap_x, gap_y = 90, 85
        for i in range(30):
            x = start_x + (i % 6) * gap_x
            y = start_y + (i // 6) * gap_y
            btn = tk.Label(self.box_canvas, image=self.add_icon, bd=2, relief="raised")
            self.box_canvas.create_window(x, y, anchor="nw", window=btn)
            btn.bind("<Button-1>", lambda e, i=i: self.start_drag(e, "box", i))
            btn.bind("<ButtonRelease-1>", self.end_drag)
            btn.bind("<Button-3>", lambda e, i=i: self.right_click("box", i))
            self.slot_buttons.append(btn)
            self.slot_positions.append((x, y))

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
    def get_sprite(self, pokemon, size=(60, 60)):
        if not pokemon:
            return self.add_icon

        key = f"{pokemon.name}_{size[0]}x{size[1]}"
        if key in self.sprite_cache:
            return self.sprite_cache[key]

        try:
            img_path = pokemon.sprite
            if not os.path.exists(img_path):
                print(f"⚠️ Sprite not found for {pokemon.name}: {img_path}")
                return self.add_icon

            img_raw = Image.open(img_path).convert("RGBA")
            img_raw = img_raw.resize(size, Image.Resampling.LANCZOS)
            img = ImageTk.PhotoImage(img_raw)
            self.sprite_cache[key] = img
            return img
        except Exception as e:
            print(f"⚠️ Failed to load sprite for {pokemon.name}: {e}")
            return self.add_icon

    # ---------------- Update Display ----------------
    def update_display(self):
        for i, mon in enumerate(self.player.party):
            sprite_img = self.get_sprite(mon)
            self.party_labels[i].image = sprite_img
            self.party_labels[i].config(text="", image=sprite_img)

        box = self.player.get_current_box()
        self.box_name_lbl.config(text=box.name)
        for i, mon in enumerate(box.pokemon):
            sprite_img = self.get_sprite(mon)
            self.slot_buttons[i].image = sprite_img
            self.slot_buttons[i].config(text="", image=sprite_img)

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

    def remove_pokemon(self, index, area="box"):
        if area == "box":
            box = self.player.get_current_box()
            mon = box.pokemon[index]
            if not mon:
                return
            confirm = messagebox.askyesno("Remove Pokémon", f"Release {mon.name}?")
            if confirm:
                box.remove_pokemon(index)
        else:
            mon = self.player.party[index]
            if not mon:
                return
            confirm = messagebox.askyesno("Remove Pokémon", f"Release {mon.name}?")
            if confirm:
                self.player.party[index] = None

        self.update_display()
        self.save_game()

    def show_pokemon(self, area, index):
        mon = self.player.party[index] if area == "party" else self.player.get_current_box().pokemon[index]
        if mon:
            messagebox.showinfo("Pokémon Info", mon.summary())
        else:
            messagebox.showinfo("Empty Slot", "No Pokémon here!")

    # ---------------- Drag and Drop ----------------
    def start_drag(self, event, area, index):
        mon = self.player.party[index] if area == "party" else self.player.get_current_box().pokemon[index]
        if not mon:
            return
        sprite_img = self.get_sprite(mon, size=(90, 90))
        floating = tk.Toplevel(self)
        floating.overrideredirect(True)
        floating.attributes("-topmost", True)
        lbl = tk.Label(floating, image=sprite_img)
        lbl.pack()
        x_root = self.winfo_pointerx() - 45
        y_root = self.winfo_pointery() - 45
        floating.geometry(f"+{x_root}+{y_root}")
        self.drag_data = {
            "pokemon": mon,
            "origin_index": index,
            "origin_area": area,
            "floating": floating,
        }
        self.bind("<Motion>", self.on_motion)
        self.bind("<ButtonRelease-1>", self.end_drag)

    def on_motion(self, event):
        floating = self.drag_data.get("floating")
        if floating:
            x_root = self.winfo_pointerx() - 45
            y_root = self.winfo_pointery() - 45
            floating.geometry(f"+{x_root}+{y_root}")

    def end_drag(self, event):
        floating = self.drag_data.get("floating")
        if not floating:
            return

        x_root = self.winfo_pointerx()
        y_root = self.winfo_pointery()

        # Check party
        target_index = None
        target_area = None
        for i, lbl in enumerate(self.party_labels):
            x1, y1 = lbl.winfo_rootx(), lbl.winfo_rooty()
            x2, y2 = x1 + lbl.winfo_width(), y1 + lbl.winfo_height()
            if x1 <= x_root <= x2 and y1 <= y_root <= y2:
                target_index = i
                target_area = "party"
                break

        # Check box
        if target_index is None:
            for i, lbl in enumerate(self.slot_buttons):
                x1, y1 = lbl.winfo_rootx(), lbl.winfo_rooty()
                x2, y2 = x1 + lbl.winfo_width(), y1 + lbl.winfo_height()
                if x1 <= x_root <= x2 and y1 <= y_root <= y2:
                    target_index = i
                    target_area = "box"
                    break

        origin_area = self.drag_data["origin_area"]
        origin_index = self.drag_data["origin_index"]
        mon = self.drag_data["pokemon"]

        # Swap if valid target
        if target_area is not None:
            if target_area == "party":
                target_list = self.player.party
            else:
                target_list = self.player.get_current_box().pokemon
            if origin_area == "party":
                origin_list = self.player.party
            else:
                origin_list = self.player.get_current_box().pokemon

            # Swap Pokémon
            target_list[target_index], origin_list[origin_index] = origin_list[origin_index], target_list[target_index]

        # Destroy floating image
        floating.destroy()
        self.drag_data = {"pokemon": None, "origin_index": None, "origin_area": None, "floating": None}
        self.unbind("<Motion>")
        self.unbind("<ButtonRelease-1>")
        self.update_display()
        self.save_game()

    def right_click(self, area, index):
        mon = self.player.party[index] if area == "party" else self.player.get_current_box().pokemon[index]
        if mon:
            choice = messagebox.askyesnocancel(
                "Pokémon Action",
                "Yes=Info, No=Release, Cancel=Do Nothing"
            )
            if choice is True:
                self.show_pokemon(area, index)
            elif choice is False:
                self.remove_pokemon(index, area)

    # ---------------- Box Navigation ----------------
    def next_box(self):
        self.player.current_box = (self.player.current_box + 1) % len(self.player.boxes)
        self.update_display()
        self.save_game()

    def prev_box(self):
        self.player.current_box = (self.player.current_box - 1) % len(self.player.boxes)
        self.update_display()
        self.save_game()


# --- MAIN ---
if __name__ == "__main__":
    player = Player()
    app = PCApp(player)
    app.mainloop()
