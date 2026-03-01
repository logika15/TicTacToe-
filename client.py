import tkinter as tk
from tkinter import messagebox, simpledialog
import socket
import threading

class GameClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Tic-Tac-Toe Race")
        
        ip = simpledialog.askstring("З'єднання", "Введіть IP сервера:", initialvalue="127.0.0.1")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((ip, 5555))
            
            data = self.sock.recv(1024).decode('utf-8').strip().split('\n')[0]
            self.my_id = int(data.split(":")[1])
            self.my_turn = False
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося підключитися: {e}")
            self.root.destroy()
            return

        self.setup_ui()
        threading.Thread(target=self.listen, daemon=True).start()

    def setup_ui(self):
        # Дорога до фінішу
        self.track = tk.Frame(self.root)
        self.track.pack(pady=10)
        self.cells = [[], []]
        for p in range(2):
            tk.Label(self.track, text=f"Гр {p+1}:").grid(row=p, column=0)
            for c in range(6):
                lbl = tk.Label(self.track, text=str(c), width=4, relief="ridge", bg="white")
                lbl.grid(row=p, column=c+1)
                self.cells[p].append(lbl)

        # Поле гри
        self.board_f = tk.Frame(self.root)
        self.board_f.pack(pady=10)
        self.btns = []
        for i in range(9):
            b = tk.Button(self.board_f, text="", font=('Arial', 18), width=5, height=2,
                          command=lambda idx=i: self.sock.send(f"MOVE:{idx}\n".encode('utf-8')))
            b.grid(row=i//3, column=i%3)
            self.btns.append(b)
            
        self.status = tk.Label(self.root, text="Очікування...", font=("Arial", 10, "bold"))
        self.status.pack()
        self.update_track(0, 0)

    def update_track(self, p1, p2):
        for i in range(6):
            self.cells[0][i].config(bg="blue" if i == p1 else "white")
            self.cells[1][i].config(bg="red" if i == p2 else "white")

    def listen(self):
        while True:
            try:
                raw_data = self.sock.recv(1024).decode('utf-8')
                if not raw_data: break
                for line in raw_data.strip().split('\n'):
                    cmd = line.split(":")
                    if cmd[0] == "UP":
                        self.btns[int(cmd[1])].config(text=cmd[2])
                    elif cmd[0] == "TURN":
                        self.my_turn = (int(cmd[1]) == self.my_id - 1)
                        self.status.config(text="ТВІЙ ХІД" if self.my_turn else "Хід суперника", fg="green" if self.my_turn else "black")
                    elif cmd[0] == "POS":
                        self.update_track(int(cmd[1]), int(cmd[2]))
                    elif cmd[0] == "RESET":
                        for b in self.btns: b.config(text="")
                    elif cmd[0] == "OVER":
                        messagebox.showinfo("Кінець", f"Гравець {cmd[1]} виграв!")
                        self.root.quit()
            except: break

if __name__ == "__main__":
    root = tk.Tk()
    GameClient(root)
    root.mainloop()