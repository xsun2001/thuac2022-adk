# AI Development Kit
# Python 3 Edition
import json
import logging
import sys
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, TypedDict
import random
import socket
import argparse
import time

# --------------------     LOGIC BEGIN    --------------------

ITEM_EXPIRE_TIME = 16


class ResultType(Enum):
    NORMAL = 0
    PLAYER_ERROR = 0x10
    ILLEGAL_ACTION = 0x11
    INVALID_FORMAT = 0x12
    INTERNAL_ERROR = 0x20


@dataclass
class Item:
    id: int
    x: int
    y: int
    time: int
    type: int
    param: int
    gotten_time: int

    item_num = 0

    def __init__(self, x: int, y: int, time: int, type: int, param: int):
        self.x = x
        self.y = y
        self.time = time
        self.type = type
        self.param = param
        self.id = Item.item_num
        self.gotten_time = -1
        Item.item_num += 1


@dataclass(init=False)
class GameConfig:
    length: int
    width: int
    max_round: int
    random_seed: int

    def __init__(self, length, width, max_round):
        self.length = length
        self.width = width
        self.max_round = max_round
        self.random_seed = int(time.time() * 1000)


@dataclass
class Snake:
    coor_list: List[Tuple[int, int]]
    item_list: List[Item]
    length_bank: int
    camp: int
    id: int

    snake_num = 0

    def __init__(self, coor_list: List[Tuple[int, int]], item_list: List[Item], camp: int, id=-1):
        self.coor_list = coor_list.copy()
        self.item_list = item_list.copy()
        self.length_bank = 0
        self.camp = camp
        if id == -1:
            self.id = Snake.snake_num
            Snake.snake_num += 1
        else:
            self.id = id

    def get_len(self) -> int:
        return len(self.coor_list)

    def add_item(self, item: Item) -> None:
        if item.type == 0:
            self.length_bank += item.param
        else:
            fl = False
            for idx in range(len(self.item_list)):
                if self.item_list[idx].type == item.type:
                    self.item_list[idx] = item
                    fl = True
                    break
            if not fl:
                self.item_list.append(item)

    def get_item(self, id: int) -> Item:
        for _item in self.item_list:
            if _item.id == id:
                return _item
        return None

    def delete_item(self, id: int) -> None:
        for _item in self.item_list:
            if _item.id == id:
                self.item_list.remove(_item)
                break


@dataclass
class Map:
    item_list: List[Item]
    wall_map: List[List[int]]
    snake_map: List[List[int]]
    item_map: List[List[int]]
    length: int
    width: int

    def __init__(self, item_list: [Item], config: GameConfig):
        self.length = config.length
        self.width = config.width
        self.item_list = item_list
        self.wall_map = [[-1 for y in range(config.width)] for x in range(config.length)]
        self.snake_map = [[-1 for y in range(config.width)] for x in range(config.length)]
        self.snake_map[0][config.width - 1] = 0
        self.snake_map[config.length - 1][0] = 1
        self.item_map = [[-1 for y in range(config.width)] for x in range(config.length)]

    def set_wall(self, coor_list: List, camp: int, type: int) -> None:
        if type == 1:
            for x, y in coor_list:
                self.wall_map[x][y] = camp
        elif type == -1:
            for x, y in coor_list:
                self.wall_map[x][y] = -1

    def get_map_item(self, id: int) -> Item:
        for _item in self.item_list:
            if _item.id == id:
                return _item
        return None

    def add_map_item(self, item: Item) -> None:
        self.item_list.append(item)
        self.item_map[item.x][item.y] = item.id

    def delete_map_item(self, id: int) -> None:
        for _item in self.item_list:
            if _item.id == id:
                self.item_map[_item.x][_item.y] = -1
                self.item_list.remove(_item)
                break

    def add_map_snake(self, coor_list: List, id: int) -> None:
        for x, y in coor_list:
            self.snake_map[x][y] = id

    def delete_map_snake(self, coor_list: List) -> None:
        for x, y in coor_list:
            self.snake_map[x][y] = -1


@dataclass
class Context:
    snake_list: List[Snake]
    game_map: Map
    turn: int
    current_player: int
    auto_growth_round: int
    max_round: int

    def __init__(self, config: GameConfig):
        self.snake_list = [
            Snake([(0, config.width - 1)], [], 0, -1),
            Snake([(config.length - 1, 0)], [], 1, -1)
        ]
        self.game_map = Map([], config)
        self.turn = 1
        self.current_player = 0
        self.auto_growth_round = 8
        self.max_round = config.max_round

    def get_map(self) -> Map:
        return self.game_map

    def get_snake_count(self, camp: int) -> int:
        return sum(x.camp == camp for x in self.snake_list)

    def get_snake(self, id: int) -> Snake:
        for _snake in self.snake_list:
            if _snake.id == id:
                return _snake

    def add_snake(self, snake: Snake, index: int) -> None:
        self.snake_list.insert(index, snake)
        self.game_map.add_map_snake(snake.coor_list, snake.id)

    def delete_snake(self, id: int):
        index = -1  # prev id of the deleted
        for _snake in self.snake_list:
            if _snake.id == id:
                self.game_map.delete_map_snake(_snake.coor_list)
                self.snake_list.remove(_snake)
                return


class Graph:
    dx = [1, 0, -1, 0]
    dy = [0, 1, 0, -1]

    def __init__(self, bound, l, w):
        self.table = [[0 for y in range(w)] for x in range(l)]
        self.l = l
        self.w = w
        self.bound = bound
        for x, y in bound:
            self.table[x][y] = -1

    def convert_dir(self, u, v):
        x = u[0] - v[0]
        y = u[1] - v[1]
        if y == 0:
            return x + 1
        if x == 0:
            return y + 2

    def check(self, c):
        for i in range(self.l):
            for j in range(self.w):
                if self.table[i][j] == c:
                    if i == 0 or j == 0 or i == self.l - 1 or j == self.w - 1:
                        return False
        return True

    def calc(self):
        for i in range(len(self.bound)):
            dir = self.convert_dir(self.bound[i], self.bound[i - 1])
            dir1 = (dir + 3) % 4
            dir2 = (dir + 1) % 4
            self.floodfill(self.bound[i][0] + self.dx[dir1], self.bound[i][1] + self.dy[dir1], 1)
            self.floodfill(self.bound[i][0] + self.dx[dir2], self.bound[i][1] + self.dy[dir2], 2)
        ret = []
        for k in range(1, 3):
            if self.check(k):
                for i in range(self.l):
                    for j in range(self.w):
                        if self.table[i][j] == k:
                            ret.append((i, j))
        return ret

    def valid(self, x, y):
        return 0 <= x < self.l and 0 <= y < self.w

    def floodfill(self, x, y, c):
        if (not self.valid(x, y)) or (self.table[x][y] != 0):
            return
        self.table[x][y] = c
        self.dfs(x, y, c)

    def dfs(self, x, y, c):
        for i in range(4):
            tx, ty = x + self.dx[i], y + self.dy[i]
            if self.valid(tx, ty) and self.table[tx][ty] == 0:
                self.table[tx][ty] = c
                self.dfs(tx, ty, c)



class Controller:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.map = ctx.get_map()
        self.player = 0
        self.next_snake = -1
        self.current_snake_list = []

    def round_preprocess(self):
        tmp_item_list = self.map.item_list.copy()
        for item in tmp_item_list:
            if item.time <= self.ctx.turn - ITEM_EXPIRE_TIME and item.gotten_time == -1:
                self.map.delete_map_item(item.id)
            if item.time == self.ctx.turn:
                snake = self.map.snake_map[item.x][item.y]
                if snake >= 0:
                    item.gotten_time = self.ctx.turn
                    self.ctx.get_snake(snake).add_item(item)
                    self.ctx.game_map.item_list.remove(item)
                else:
                    self.map.item_map[item.x][item.y] = item.id
        for snake in self.ctx.snake_list:
            for item in snake.item_list:
                if self.ctx.turn - item.gotten_time > item.param:
                    snake.delete_item(item.id)
        return

    def find_next_snake(self):
        for idx, (snake, dead) in enumerate(self.current_snake_list[self.next_snake + 1::]):
            if snake.camp == self.player and not dead:
                self.next_snake = self.next_snake + 1 + idx
                return
        self.next_snake = -1

    def next_player(self):
        self.player = self.ctx.current_player = 1 - self.ctx.current_player
        if self.player == 0:
            self.ctx.turn = 1 + self.ctx.turn
        self.next_snake = -1

    def delete_snake(self, s_id: int):
        self.ctx.delete_snake(s_id)
        temp = self.current_snake_list
        self.current_snake_list = [(i, i.id == s_id or dead) for (i, dead) in temp]

    def round_init(self):
        self.current_snake_list = [(i, False) for i in self.ctx.snake_list]
        self.find_next_snake()

    def apply(self, op: int):
        if not self.apply_single(self.next_snake, op):
            return False
        self.find_next_snake()
        return True

    def calc(self, coor: [(int, int)]) -> [(int, int)]:
        g = Graph(coor, self.map.length, self.map.width)
        return g.calc()

    def apply_single(self, snake: int, op: int):
        s, _ = self.current_snake_list[snake]
        idx_in_ctx = -1
        for idx, t in enumerate(self.ctx.snake_list):
            if s.id == t.id:
                idx_in_ctx = idx
        assert (idx_in_ctx != -1)
        if op <= 4:  # move
            return self.move(idx_in_ctx, op - 1)
        elif op == 5:
            if len(self.ctx.snake_list[idx_in_ctx].item_list) == 0:
                return False
            elif self.ctx.snake_list[idx_in_ctx].item_list[0].type == 2:
                return self.fire(idx_in_ctx)
            else:
                return False
        elif op == 6:
            return self.split(idx_in_ctx)
        else:
            return False

    def get_item(self, snake: Snake, item_id: int) -> None:
        item = self.map.get_map_item(item_id)
        item.gotten_time = self.ctx.turn
        if item.type == 0:
            snake.length_bank += item.param
        else:
            snake.add_item(item)
        self.map.delete_map_item(item_id)

    def move(self, idx_in_ctx: int, direction: int):
        dx = [1, 0, -1, 0]
        dy = [0, 1, 0, -1]
        snake = self.ctx.snake_list[idx_in_ctx]
        snake_id = snake.id
        auto_grow = self.ctx.turn <= self.ctx.auto_growth_round and snake.camp == snake.id
        coor = snake.coor_list
        x, y = coor[0][0] + dx[direction], coor[0][1] + dy[direction]
        if len(coor) == 1:
            new_coor = [(x, y)]
        else:
            new_coor = [(x, y)] + coor[:-1]

        if (len(coor) > 2 or (len(coor) == 2 and (auto_grow or snake.length_bank))) and (x, y) == coor[1]:
            return False

        self.ctx.delete_snake(snake_id)

        if x < 0 or x >= self.ctx.game_map.length or y < 0 or y >= self.ctx.game_map.width \
                or self.map.wall_map[x][y] != -1:
            self.delete_snake(snake_id)
            return True

        if auto_grow:
            new_coor = new_coor + [coor[-1]]
        elif snake.length_bank:
            snake.length_bank = snake.length_bank - 1
            new_coor = new_coor + [coor[-1]]
        snake.coor_list = new_coor

        if self.map.item_map[x][y] != -1:
            self.get_item(snake, self.map.item_map[x][y])

        for i in range(len(new_coor)):
            if i == 0:
                continue
            if x == new_coor[i][0] and y == new_coor[i][1]:
                dead_snake = [snake_id]
                solid_coor = new_coor[:i]
                extra_solid = self.calc(solid_coor)
                for coor in new_coor[i:]:
                    if coor in extra_solid:
                        solid_coor.append(coor)
                        extra_solid.remove(coor)
                tmp_solid = extra_solid.copy()
                for coor in tmp_solid:
                    if self.map.snake_map[coor[0]][coor[1]] != -1:
                        dead_snake.append(self.map.snake_map[coor[0]][coor[1]])
                        self.delete_snake(dead_snake[-1])
                self.map.set_wall(solid_coor, self.player, 1)
                self.map.set_wall(extra_solid, self.player, 1)
                self.delete_snake(snake_id)
                return True

        if self.map.snake_map[x][y] != -1:
            self.delete_snake(snake_id)
            return True

        self.ctx.add_snake(snake, idx_in_ctx)
        return True

    def split(self, idx_in_ctx: int):
        def generate(pos, its, player, length_bank, index) -> int:
            ret = Snake(pos, its, player, -1)
            ret.length_bank = length_bank
            self.ctx.add_snake(ret, index)
            return ret.id

        snake = self.ctx.snake_list[idx_in_ctx]
        coor = snake.coor_list
        items = snake.item_list

        if self.ctx.get_snake_count(snake.camp) >= 4:
            return False

        if len(coor) <= 1:
            return False

        head = coor[:(len(coor) + 1) // 2]
        tail = coor[(len(coor) + 1) // 2:]
        tail = tail[::-1]

        h_item = []
        t_item = []

        for item in items:
            if item.type == 0:
                t_item.append(item)
            elif item.type == 1:
                continue
            else:
                h_item.append(item)

        snake.coor_list = head
        snake.item_list = h_item
        generate(tail, t_item, self.player, snake.length_bank, idx_in_ctx + 1)
        snake.length_bank = 0
        return True

    def fire(self, idx_in_ctx: int):
        snake = self.ctx.snake_list[idx_in_ctx]
        coor = snake.coor_list

        if len(coor) <= 1:
            return False

        snake.item_list.pop(0)
        x1, y1 = coor[0]
        x2, y2 = coor[1]
        dx, dy = x1 - x2, y1 - y2
        walls = []

        while self.map.length > x1 + dx >= 0 and self.map.width > y1 + dy >= 0:
            x1, y1 = (x1 + dx, y1 + dy)
            walls = [(x1, y1)] + walls

        self.map.set_wall(walls, -1, -1)
        return True


# --------------------     LOGIC END    --------------------


# --------------------     Client BEGIN    --------------------


class Client:
    # 0 Game Config
    # 1 Item List
    # 2 Operations
    __state = 0
    __buf = []
    __int_buf = [0, 0]
    __my_player = 0
    __current_player = 0
    __client = None
    __local = False

    def __init__(self):
        logging.basicConfig(format='%(levelname)s:[ADK.%(module)s:%(lineno)d]: %(message)s', stream=sys.stderr,
                            level=logging.ERROR)
        if len(sys.argv) == 1:
            self.__local = False
        elif len(sys.argv) == 3:
            self.__local = True
            self.__client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__client.connect((sys.argv[1], int(sys.argv[2])))
        else:
            raise RuntimeError

    def __from_B(self):
        if self.__local:
            return int.from_bytes(self.__client.recv(1), byteorder='big', signed=False)
        else:
            return int.from_bytes(sys.stdin.buffer.read(1), byteorder='big', signed=False)

    def __from_I(self):
        if self.__local:
            return int.from_bytes(self.__client.recv(2), byteorder='big', signed=True)
        else:
            return int.from_bytes(sys.stdin.buffer.read(2), byteorder='big', signed=True)

    def fetch_data(self):
        if self.__state == 0:
            res = []
            for i in range(4):
                res.append(self.__from_B()) if i != 2 else res.append(self.__from_I())
            self.__my_player = res[3]
            self.__state = 1
            return res
        elif self.__state == 1:
            _ = self.__from_B()
            len = self.__from_I()
            res = []
            for i in range(len):
                res.append(Item(x=self.__from_B(), y=self.__from_B(), type=self.__from_B(), time=self.__from_I(), param=self.__from_I()))
            logging.debug("Item list loaded. Total count %d.", len)
            self.__state = 2
            return res
        elif self.__state == 2:
            type = self.__from_B()
            if type == 0x11:
                res = [-1, ResultType(self.__from_B()), self.__from_B(), self.__from_I(), self.__from_I()]
                if self.__local:
                    self.__client.close()
                return res
            return [type]

    def send_data(self, data):
        logging.debug('Sending data: ' + str(data))
        msg = data.to_bytes(1, byteorder='big', signed=False)
        if data < 1 or data > 6:
            raise RuntimeError("Illegal Operation")
        len_byte = len(msg).to_bytes(4, 'big', signed=True)
        msg_byte = len_byte + msg
        if self.__local:
            self.__client.send(msg_byte)
        else:
            sys.stdout.buffer.write(msg_byte)
            sys.stdout.flush()


# --------------------     Client END    --------------------
