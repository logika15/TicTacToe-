import socket
import threading
import time
import random

class Server:
    def __init__(self):
        print("=== НАЛАШТУВАННЯ СЕРВЕРА ===")
        self.size = int(input("Розмір поля (3, 5 або 10): ") or 3)
        self.win_req = 3 if self.size == 3 else 5
        self.use_traps = input("Увімкнути ловушки та магазин? (y/n): ").lower() == 'y'
        self.traps_count = int(input("Кількість ловушок: ") or 0) if self.use_traps else 0
        
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('0.0.0.0', 5555))
        self.server.listen(2)
        
        self.clients = []
        self.shield = [False, False] # Флаг защиты от ловушек
        self.reset_game_state()
        print(f"\n>>> СЕРВЕР ЗАПУЩЕНО. Чекаємо гравців...")

    def reset_game_state(self):
        self.race_pos = [0, 0]
        self.coins = [0, 0]
        self.wins_streak = [0, 0]
        self.has_bonus = [False, False]
        self.board = [""] * (self.size * self.size)
        self.turn = 0
        self.bonus_moves_left = 0
        self.ready_to_restart = [False, False]
        self.shield = [False, False]
        if self.use_traps: self.generate_traps()

    def generate_traps(self):
        self.traps = random.sample(range(self.size * self.size), self.traps_count)

    def broadcast(self, msg):
        for c in self.clients:
            try: c.sendall((msg + "\n").encode('utf-8'))
            except: pass

    def check_winner(self):
        s, w, b = self.size, self.win_req, self.board
        for r in range(s):
            for c in range(s):
                if b[r*s+c] == "": continue
                char = b[r*s+c]
                for dr, dc in [(0,1), (1,0), (1,1), (1,-1)]:
                    count = 0
                    for i in range(w):
                        nr, nc = r + dr*i, c + dc*i
                        if 0 <= nr < s and 0 <= nc < s and b[nr*s+nc] == char: count += 1
                        else: break
                    if count == w: return char
        return "DRAW" if "" not in b else None

    def handle(self, conn, p_idx):
        while True:
            try:
                raw_data = conn.recv(1024).decode('utf-8')
                if not raw_data: break
                for line in raw_data.strip().split('\n'):
                    if not line: continue
                    
                    if line == "RESTART_YES":
                        self.ready_to_restart[p_idx] = True
                        if all(self.ready_to_restart):
                            self.reset_game_state()
                            self.broadcast("GAME_RESTART")
                            self.broadcast("LOG:Гра перезапущена!")
                            self.broadcast("POS:0:0")
                            self.broadcast("COINS:0:0")
                            self.broadcast("RESET")
                            self.broadcast("TURN:0:NORMAL")

                    elif line.startswith("BUY:") and self.use_traps:
                        item = line.split(":")[1]
                        if item == "SCAN" and self.coins[p_idx] >= 2:
                            self.coins[p_idx] -= 2
                            conn.send(f"TRAPS:{','.join(map(str, self.traps))}\n".encode('utf-8'))
                            self.broadcast(f"LOG:Гравець {p_idx+1} використав сканер")
                        elif item == "SHIELD" and self.coins[p_idx] >= 2:
                            self.coins[p_idx] -= 2
                            self.shield[p_idx] = True
                            self.broadcast(f"LOG:Гравець {p_idx+1} купив щит 🛡️")
                        elif item == "STEAL" and self.coins[p_idx] >= 3:
                            self.coins[p_idx] -= 3
                            stolen = min(2, self.coins[1-p_idx])
                            self.coins[1-p_idx] -= stolen
                            self.coins[p_idx] += stolen
                            self.broadcast(f"LOG:Гравець {p_idx+1} вкрав {stolen}💰")
                        self.broadcast(f"COINS:{self.coins[0]}:{self.coins[1]}")

                    elif line.startswith("MOVE:") and p_idx == self.turn:
                        idx = int(line.split(":")[1])
                        if self.board[idx] == "":
                            if self.use_traps and idx in self.traps:
                                self.traps.remove(idx)
                                if self.shield[p_idx]:
                                    self.shield[p_idx] = False
                                    self.broadcast(f"LOG:Гравець {p_idx+1} витримав вибух щитом!")
                                    self.broadcast(f"TRAP_HIT:{idx}:SHIELD")
                                else:
                                    stolen = min(1, self.coins[p_idx])
                                    self.coins[p_idx] -= stolen
                                    self.broadcast(f"TRAP_HIT:{idx}:BOOM")
                                    self.broadcast(f"LOG:Гравець {p_idx+1} підірвався (-1💰)")
                                    self.bonus_moves_left = 0
                                    self.broadcast(f"COINS:{self.coins[0]}:{self.coins[1]}")
                                    self.end_turn()
                                    continue

                            char = "X" if p_idx == 0 else "O"
                            self.board[idx] = char
                            self.broadcast(f"UP:{idx}:{char}")
                            res = self.check_winner()
                            if res: self.process_round_end(res)
                            else:
                                if self.bonus_moves_left > 0:
                                    self.bonus_moves_left -= 1
                                    self.broadcast(f"TURN:{self.turn}:BONUS")
                                else: self.end_turn()
            except: break

    def end_turn(self):
        self.turn = 1 - self.turn
        mode = "DOUBLE" if self.has_bonus[self.turn] else "NORMAL"
        if mode == "DOUBLE":
            self.bonus_moves_left = 1
            self.has_bonus[self.turn] = False
        self.broadcast(f"TURN:{self.turn}:{mode}")

    def process_round_end(self, res):
        time.sleep(0.5)
        if res != "DRAW":
            idx = 0 if res == "X" else 1
            self.race_pos[idx] = min(5, self.race_pos[idx] + 1)
            self.wins_streak[idx] += 1
            self.wins_streak[1-idx] = 0
            self.coins[idx] += 3
            if self.wins_streak[idx] >= 2: self.has_bonus[idx] = True
            self.broadcast(f"LOG:Раунд виграв Гравець {idx+1}")
        else:
            self.wins_streak = [0, 0]
            self.broadcast("LOG:Нічия у раунді")
        
        self.board = [""] * (self.size * self.size)
        if self.use_traps: self.generate_traps()
        self.broadcast(f"POS:{self.race_pos[0]}:{self.race_pos[1]}")
        self.broadcast(f"COINS:{self.coins[0]}:{self.coins[1]}")
        self.broadcast("RESET")
        if 5 in self.race_pos: self.broadcast(f"OVER:{1 if self.race_pos[0]==5 else 2}")
        else:
            self.turn = 0
            self.end_turn() # Используем общую логику передачи хода

if __name__ == "__main__":
    Server().start()
