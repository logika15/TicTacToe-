import tkinter as tk
from tkinter import messagebox, simpledialog
import socket
import threading

class GameClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Cyber Tic-Tac-Toe")
        self.root.configure(bg="#1a1a1a")
        
        # Ввод IP
        ip = simpledialog.askstring("Connect", "Введіть IP сервера:", initialvalue="127.0.0.1")
        if not ip:
            self.root.destroy()
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((ip, 5555))
            
            # Читаем конфиг: ID:SIZE:TRAPS_ON
            data = self.sock.recv(1024).decode('utf-8').strip().split(':')
            self.my_id = int(data[1])
            self.size = int(data[2])
            self.traps_on = (data[3] == "1")
            
            self.my_turn = False
            self.sock.settimeout(None)
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося підключитися: {e}")
            self.root.destroy()
            return

        self.setup_ui()
        threading.Thread(target=self.listen, daemon=True).start()

    def setup_ui(self):
        # Верхняя панель (Статус и Монеты)
        self.header = tk.Frame(self.root, bg="#333", pady=5)
        self.header.pack(fill="x")
        
        self.coin_lbl = tk.Label(self.header, text="💰: 0", font=("Arial", 12, "bold"), fg="#ffd700", bg="#333")
        if self.traps_on:
            self.coin_lbl.pack(side="left", padx=15)
        
        self.status = tk.Label(self.header, text="Чекаємо на суперника...", font=("Arial", 11), fg="white", bg="#333")
        self.status.pack(side="right", padx=15)

        # Прогресс гонки
        self.track_f = tk.Frame(self.root, bg="#1a1a1a", pady=10)
        self.track_f.pack()
        self.cells = [[], []]
        for p in range(2):
            tk.Label(self.track_f, text=f"P{p+1}", fg="white", bg="#1a1a1a", font=("Arial", 8)).grid(row=p, column=0, padx=5)
            for c in range(6):
                l = tk.Label(self.track_f, text=" ", width=3, bg="#444", relief="flat")
                l.grid(row=p, column=c+1, padx=2, pady=2)
                self.cells[p].append(l)

        # Контейнер для поля и магазина
        self.main_f = tk.Frame(self.root, bg="#1a1a1a")
        self.main_f.pack(pady=10, padx=10)

        # Игровое поле
        self.board_f = tk.Frame(self.main_f, bg="#1a1a1a")
        self.board_f.pack(side="left")
        self.btns = []
        
        # Адаптивный размер шрифта
        f_size = 14 if self.size == 3 else 10
        for i in range(self.size**2):
            b = tk.Button(self.board_f, text="", font=("Arial", f_size, "bold"), width=4, height=2, 
                          bg="#222", fg="white", activebackground="#444",
                          command=lambda idx=i: self.sock.send(f"MOVE:{idx}\n".encode('utf-8')))
            b.grid(row=i//self.size, column=i%self.size, padx=1, pady=1)
            self.btns.append(b)

        # Боковая панель (Магазин и Лог)
        self.side_f = tk.Frame(self.main_f, bg="#1a1a1a")
        self.side_f.pack(side="right", fill="y", padx=10)

        if self.traps_on:
            shop = tk.LabelFrame(self.side_f, text=" МАГАЗИН ", fg="white", bg="#1a1a1a")
            shop.pack(fill="x", pady=5)
            tk.Button(shop, text="Сканер (2💰)", bg="#4682b4", fg="white", command=lambda: self.sock.send(b"BUY:SCAN\n")).pack(fill="x", pady=2)
            tk.Button(shop, text="Щит (2💰)", bg="#2e8b57", fg="white", command=lambda: self.sock.send(b"BUY:SHIELD\n")).pack(fill="x", pady=2)
            tk.Button(shop, text="Крадій (3💰)", bg="#cd5c5c", fg="white", command=lambda: self.sock.send(b"BUY:STEAL\n")).pack(fill="x", pady=2)

        self.log_box = tk.Listbox(self.side_f, width=30, height=8, bg="black", fg="#00ff00", font=("Consolas", 9), border=0)
        self.log_box.pack(pady=5)
        self.log_box.insert("end", "Система готова...")

    def add_log(self, text):
        self.log_box.insert("end", f"> {text}")
        self.log_box.see("end")

    def listen(self):
        while True:
            try:
                raw = self.sock.recv(1024).decode('utf-8')
                if not raw: break
                for line in raw.strip().split('\n'):
                    cmd = line.split(":")
                    if cmd[0] == "UP":
                        char = cmd[2]
                        color = "#00e5ff" if char == "X" else "#ff4081"
                        self.btns[int(cmd[1])].config(text=char, state="disabled", disabledforeground=color)
                    elif cmd[0] == "TURN":
                        self.my_turn = (int(cmd[1]) == self.my_id - 1)
                        bonus = " [X2!]" if "DOUBLE" in line or "BONUS" in line else ""
                        self.status.config(text=f"{'ТВІЙ ХІД' if self.my_turn else 'Хід суперника'}{bonus}", 
                                          fg="#00ff00" if self.my_turn else "#ff4444")
                    elif cmd[0] == "COINS":
                        self.coin_lbl.config(text=f"💰: {cmd[self.my_id]}")
                    elif cmd[0] == "TRAP_HIT":
                        # Если щит сработал, цвет другой
                        color = "#ff8c00" if len(cmd) > 2 and cmd[2] == "SHIELD" else "#ff0000"
                        self.btns[int(cmd[1])].config(text="💥", bg=color)
                    elif cmd[0] == "LOG":
                        self.add_log(cmd[1])
                    elif cmd[0] == "TRAPS":
                        for i in cmd[1].split(','):
                            self.btns[int(i)].config(bg="#3d2b2b")
                    elif cmd[0] == "POS":
                        colors = ["#00e5ff", "#ff4081"]
                        for p in range(2):
                            p_pos = int(cmd[p+1])
                            for i in range(6):
                                self.cells[p][i].config(bg=colors[p] if i == p_pos else "#444")
                    elif cmd[0] == "RESET":
                        for b in self.btns:
                            b.config(text="", state="normal", bg="#222")
                    elif cmd[0] == "OVER":
                        res = messagebox.askyesno("Кінець гри", f"Гравець {cmd[1]} переміг!\nБажаєте реванш?")
                        if res: self.sock.send(b"RESTART_YES\n")
                        else: self.root.quit()
                    elif cmd[0] == "GAME_RESTART":
                        self.log_box.delete(0, "end")
                        self.add_log("ГРА ПЕРЕЗАПУЩЕНА!")
            except: break

if __name__ == "__main__":
    root = tk.Tk()
    app = GameClient(root)
    root.mainloop()
