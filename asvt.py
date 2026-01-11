import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as fd
import math
import json

CLR_BG = "#141415"
CLR_SIDEBAR = "#1C1C1D"
CLR_CANVAS = "#161617"
CLR_GRID = "#222223"
CLR_TEXT = "#E0E0E0"
CLR_ON = "#00E676"
CLR_OFF = "#37474F"
CLR_PIN_IN = "#2979FF"
CLR_PIN_OUT = "#FF5252"
CLR_WIRE = "#455A64"
GATE_WIDTH, GATE_HEIGHT = 70, 46
CORNER_RADIUS = 20

class Gate:
    def __init__(self, x, y, gate_type, name=None):
        self.x, self.y = x, y
        self.type = gate_type
        self.name = name or f"{gate_type}_{int(math.fmod(id(self), 10000))}"
        self.output = False
        if gate_type in ['AND', 'OR', 'XOR', 'NAND', 'NOR', 'XNOR']: self.input_count = 2
        elif gate_type in ['NOT', 'LED', 'NODE']: self.input_count = 1
        else: self.input_count = 0 
        self.connected_inputs = [None] * self.input_count 

    def get_input_pos_idx(self, index):
        if self.type == 'NODE': return (self.x, self.y)
        step = GATE_HEIGHT / (self.input_count + 1)
        return (self.x, self.y + step * (index + 1))

    def get_output_pos(self):
        if self.type == 'NODE': return (self.x, self.y)
        return (self.x + GATE_WIDTH, self.y + GATE_HEIGHT / 2)

    def is_inside(self, x, y):
        if self.type == 'NODE': return math.hypot(x - self.x, y - self.y) < 15
        return self.x <= x <= self.x + GATE_WIDTH and self.y <= y <= self.y + GATE_HEIGHT

    def compute(self):
        vals = [conn[0].output if conn else False for conn in self.connected_inputs]
        if self.type == 'AND': self.output = all(vals) if vals else False
        elif self.type == 'OR': self.output = any(vals) if vals else False
        elif self.type == 'NOT': self.output = not vals[0] if vals else True
        elif self.type == 'XOR': self.output = sum(vals) % 2 == 1 if vals else False
        elif self.type == 'NAND': self.output = not all(vals) if vals else True
        elif self.type == 'NOR': self.output = not any(vals) if vals else True
        elif self.type == 'XNOR': self.output = sum(vals) % 2 == 0 if vals else True
        elif self.type in ['LED', 'NODE']: self.output = vals[0] if vals else False

class LogicSimPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Logic System")
        self.root.geometry("1200x850")
        self.gates = []
        self.drag_item = None
        self.wiring_start = None 
        self.mouse_pos = (0, 0)
        self.setup_ui()
        self.update_logic()

    def round_rect(self, x, y, w, h, r, **kwargs):
        p = [x+r, y, x+w-r, y, x+w, y, x+w, y+r, x+w, y+h-r, x+w, y+h, x+w-r, y+h, x+r, y+h, x, y+h, x, y+h-r, x, y+r, x, y]
        return self.canvas.create_polygon(p, smooth=True, **kwargs)

    def setup_ui(self):
        self.root.configure(bg=CLR_BG)
        sidebar = tk.Frame(self.root, bg=CLR_SIDEBAR, width=200, padx=10, pady=10)
        sidebar.pack(side="left", fill="y")
        btns = [
            ("ВВОД", [("Switch", "SW"), ("Node", "NODE")]),
            ("ВЫВОД", [("LED", "LED")]),
            ("ЛОГИКА", [("AND", "AND"), ("OR", "OR"), ("NOT", "NOT"), ("XOR", "XOR")]),
            ("ИНВЕРСИЯ", [("NAND", "NAND"), ("NOR", "NOR"), ("XNOR", "XNOR")])
        ]
        for lbl, items in btns:
            tk.Label(sidebar, text=lbl, bg=CLR_SIDEBAR, fg="#555", font=("Arial", 8, "bold")).pack(pady=(10, 2), anchor="w")
            for text, gtype in items:
                tk.Button(sidebar, text=text, bg="#2A2A2B", fg=CLR_TEXT, bd=0, command=lambda t=gtype: self.add_gate(t)).pack(fill="x", pady=2, ipady=3)
        tk.Frame(sidebar, height=2, bg="#333").pack(fill="x", pady=10)
        tk.Button(sidebar, text="СОХРАНИТЬ", bg="#2E7D32", fg="white", bd=0, command=self.save_schema).pack(fill="x", pady=2, ipady=5)
        tk.Button(sidebar, text="ЗАГРУЗИТЬ", bg="#1565C0", fg="white", bd=0, command=self.load_schema).pack(fill="x", pady=2, ipady=5)
        tk.Button(sidebar, text="ТАБЛИЦА", bg="#424242", fg=CLR_ON, bd=0, command=self.show_truth_table).pack(fill="x", pady=(10, 0), ipady=5)
        self.canvas = tk.Canvas(self.root, bg=CLR_CANVAS, highlightthickness=0)
        self.canvas.pack(side="right", expand=True, fill="both")
        self.canvas.bind("<Button-1>", self.on_left_down)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, 'drag_item', None))
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-2>", self.on_middle_click)

    def add_gate(self, gtype, x=150, y=150, name=None):
        g = Gate(x, y, gtype, name)
        self.gates.append(g)
        self.draw()
        return g

    def save_schema(self):
        data = []
        for g in self.gates:
            conns = [c[0].name if c else None for c in g.connected_inputs]
            data.append({'n': g.name, 't': g.type, 'x': g.x, 'y': g.y, 'c': conns})
        f = fd.asksaveasfilename(defaultextension=".json")
        if f:
            with open(f, 'w') as file: json.dump(data, file)

    def load_schema(self):
        f = fd.askopenfilename(filetypes=[("JSON", "*.json")])
        if not f: return
        with open(f, 'r') as file: data = json.load(file)
        self.gates = []
        name_map = {}
        for d in data:
            g = self.add_gate(d['t'], d['x'], d['y'], d['n'])
            name_map[d['n']] = g
        for d in data:
            g = name_map[d['n']]
            for i, c_name in enumerate(d['c']):
                if c_name in name_map: g.connected_inputs[i] = (name_map[c_name], 0)
        self.draw()

    def on_left_down(self, event):
        for g in reversed(self.gates):
            if g.is_inside(event.x, event.y):
                if g.type == 'SW': g.output = not g.output
                self.drag_item = g
                self.drag_offset = (event.x - g.x, event.y - g.y)
                self.gates.remove(g); self.gates.append(g)
                self.draw(); return

    def on_drag(self, event):
        if self.drag_item:
            self.drag_item.x, self.drag_item.y = event.x - self.drag_offset[0], event.y - self.drag_offset[1]
            self.draw()

    def on_right_click(self, event):
        t = self.find_pin_at(event.x, event.y)
        if not t: self.wiring_start = None
        elif self.wiring_start is None: self.wiring_start = t
        else:
            s_g, s_o, s_i = self.wiring_start
            t_g, t_o, t_i = t
            if (s_o != t_o) or (t_g.type == 'NODE' or s_g.type == 'NODE'):
                if s_o: t_g.connected_inputs[t_i] = (s_g, 0)
                else: s_g.connected_inputs[s_i] = (t_g, 0)
                self.wiring_start = None
            else: self.wiring_start = t
        self.draw()

    def on_middle_click(self, event):
        for g in self.gates:
            if g.type == 'NODE' and g.is_inside(event.x, event.y):
                self.remove_gate(g)
                self.draw(); return

        t = self.find_pin_at(event.x, event.y)
        if t:
            gate, is_out, idx = t
            if not is_out: gate.connected_inputs[idx] = None
            else:
                for other in self.gates:
                    for i, c in enumerate(other.connected_inputs):
                        if c and c[0] == gate: other.connected_inputs[i] = None
            self.draw(); return

        for g in self.gates:
            if g.is_inside(event.x, event.y):
                self.remove_gate(g)
                self.draw(); return

    def remove_gate(self, gate_obj):
        if gate_obj in self.gates:
            self.gates.remove(gate_obj)
            for o in self.gates:
                for i, c in enumerate(o.connected_inputs):
                    if c and c[0] == gate_obj: o.connected_inputs[i] = None

    def find_pin_at(self, x, y):
        for g in self.gates:
            if g.type == 'NODE':
                if math.hypot(x-g.x, y-g.y) < 15: return (g, self.wiring_start is None, 0)
            if g.type != 'LED':
                p = g.get_output_pos()
                if math.hypot(x-p[0], y-p[1]) < 12: return (g, True, 0)
            for i in range(g.input_count):
                p = g.get_input_pos_idx(i)
                if math.hypot(x-p[0], y-p[1]) < 12: return (g, False, i)
        return None

    def on_mouse_move(self, event):
        self.mouse_pos = (event.x, event.y)
        if self.wiring_start: self.draw()

    def update_logic(self):
        for _ in range(3):
            for g in self.gates: g.compute()
        self.draw()
        self.root.after(50, self.update_logic)

    def show_truth_table(self):
        sw, out = [g for g in self.gates if g.type == 'SW'], [g for g in self.gates if g.type == 'LED']
        if not sw: return
        w = tk.Toplevel(self.root)
        w.configure(bg=CLR_SIDEBAR)
        c = [s.name for s in sw] + ["|"] + [o.name for o in out]
        t = ttk.Treeview(w, columns=c, show='headings', height=10)
        for col in c: t.heading(col, text=col); t.column(col, width=60, anchor="center")
        t.pack(padx=10, pady=10)
        orig = [s.output for s in sw]
        for i in range(2**len(sw)):
            r = []
            for j, s in enumerate(sw):
                s.output = bool((i >> (len(sw)-1-j)) & 1); r.append(1 if s.output else 0)
            for _ in range(5): 
                for g in self.gates: g.compute()
            r.append("|")
            for o in out: r.append(1 if o.output else 0)
            t.insert("", "end", values=r)
        for s, v in zip(sw, orig): s.output = v

    def draw(self):
        self.canvas.delete("all")
        for i in range(0, 1600, 40):
            self.canvas.create_line(i, 0, i, 1200, fill=CLR_GRID)
            self.canvas.create_line(0, i, 1600, i, fill=CLR_GRID)
        for g in self.gates:
            for i, c in enumerate(g.connected_inputs):
                if c:
                    p1, p2 = c[0].get_output_pos(), g.get_input_pos_idx(i)
                    clr = CLR_ON if c[0].output else CLR_WIRE
                    self.canvas.create_line(p1[0], p1[1], p1[0]+25, p1[1], p2[0]-25, p2[1], p2[0], p2[1], fill=clr, width=3, smooth=True)
        if self.wiring_start:
            s_g, s_o, s_i = self.wiring_start
            p1 = s_g.get_output_pos() if s_o else s_g.get_input_pos_idx(s_i)
            self.canvas.create_line(p1[0], p1[1], self.mouse_pos[0], self.mouse_pos[1], fill=CLR_ON, dash=(4,2))
        for g in self.gates:
            if g.type == 'NODE':
                self.canvas.create_oval(g.x-6, g.y-6, g.x+6, g.y+6, outline=CLR_PIN_OUT, width=2, fill="#555")
                self.canvas.create_oval(g.x-2, g.y-2, g.x+2, g.y+2, fill=CLR_ON if g.output else "#333")
            else:
                bg = "#2C2C2E"
                if g.type in ['SW', 'LED'] and g.output: bg = "#004D40"
                self.round_rect(g.x, g.y, GATE_WIDTH, GATE_HEIGHT, CORNER_RADIUS, fill=bg, outline="#444", width=2)
                self.canvas.create_text(g.x+GATE_WIDTH/2, g.y+GATE_HEIGHT/2, text=g.type, fill=CLR_TEXT, font=("Segoe UI", 9, "bold"))
                for i in range(g.input_count):
                    p = g.get_input_pos_idx(i); self.canvas.create_oval(p[0]-4, p[1]-4, p[0]+4, p[1]+4, fill=CLR_PIN_IN, outline="")
                if g.type != 'LED':
                    p = g.get_output_pos(); self.canvas.create_oval(p[0]-4, p[1]-4, p[0]+4, p[1]+4, fill=CLR_PIN_OUT, outline="")

if __name__ == "__main__":
    root = tk.Tk(); app = LogicSimPro(root); root.mainloop()