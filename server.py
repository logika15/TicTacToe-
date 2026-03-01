import socket
import threading
import time

class Server:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('0.0.0.0', 5555))
        self.server.listen(2)
        self.clients = []
        self.positions = [0, 0]
        self.board = [""] * 9
        self.turn = 0
        print(">>> СЕРВЕР ЗАПУЩЕНО. Очікуємо 2 гравців...")

    def broadcast(self, msg):
        full_msg = (msg + "\n").encode('utf-8')
        for c in self.clients:
            try:
                c.sendall(full_msg)
            except:
                pass

    def check_winner(self):
        b = self.board
        wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
        for c in wins:
            if b[c[0]] == b[c[1]] == b[c[2]] != "":
                return b[c[0]]
        if "" not in b: return "DRAW"
        return None

    def handle(self, conn, p_idx):
        while True:
            try:
                data = conn.recv(1024).decode('utf-8').strip()
                if not data: break
                
                if data.startswith("MOVE:") and p_idx == self.turn:
                    idx = int(data.split(":")[1])
                    if self.board[idx] == "":
                        char = "X" if p_idx == 0 else "O"
                        self.board[idx] = char
                        self.broadcast(f"UP:{idx}:{char}")
                        
                        res = self.check_winner()
                        if res:
                            time.sleep(0.5)
                            
                            # НОВА ЛОГІКА ТУТ:
                            # Якщо переміг X (гравець 1)
                            if res == "X":
                                self.positions[0] = min(5, self.positions[0] + 1)
                            # Якщо переміг O (гравець 2)
                            elif res == "O":
                                self.positions[1] = min(5, self.positions[1] + 1)
                            # При нічиї (res == "DRAW") позиції НЕ змінюються
                            
                            self.board = [""] * 9
                            self.broadcast(f"POS:{self.positions[0]}:{self.positions[1]}")
                            self.broadcast("RESET")
                            
                            if 5 in self.positions:
                                win_num = 1 if self.positions[0] == 5 else 2
                                self.broadcast(f"OVER:{win_num}")
                                break
                            
                            self.turn = 0 
                            self.broadcast("TURN:0")
                        else:
                            self.turn = 1 - self.turn
                            self.broadcast(f"TURN:{self.turn}")
            except: break

    def start(self):
        while len(self.clients) < 2:
            conn, addr = self.server.accept()
            self.clients.append(conn)
            conn.send(f"ID:{len(self.clients)}\n".encode('utf-8'))
            print(f"Гравець {len(self.clients)} підключився.")
        
        threading.Thread(target=self.handle, args=(self.clients[0], 0), daemon=True).start()
        threading.Thread(target=self.handle, args=(self.clients[1], 1), daemon=True).start()
        self.broadcast("TURN:0")
        while True: time.sleep(1)

if __name__ == "__main__":
    Server().start()