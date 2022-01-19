from adk import *

# written by lbr

dx = [1, 0, -1, 0]
dy = [0, 1, 0, -1]
INF = 1e9
# constants

SPLIT_LIMIT = 10
SEARCH_LIMIT = 100
# tunable parameters


class AI:
    """
    This AI proceeds according to following rules:

    The first snake is active, all other snakes split by the first snake are passive.

    An active snake will act according to self.active_strategy.

    A passive snake will act according to self.passive_strategy.

    Check those functions for detail.
    """
    def __init__(self):
        self.ctx = None
        self.snake = None
        self.order = dict()

    def check(self, op):
        """
        :param op: the direction
        :return: True if this move is legal and will not result in solidification.
                 False otherwise.
        """
        x = self.snake.coor_list[0][0] + dx[op]
        y = self.snake.coor_list[0][1] + dy[op]
        if x < 0 or y < 0 or x >= 16 or y >= 16 or self.ctx.game_map.wall_map[x][y] != -1:
            return False
        # check wall and out of bounds
        if self.snake.get_len() > 1 and x == self.snake.coor_list[1][0] and y == self.snake.coor_list[1][1]:
            return False
        # check turn back
        if self.ctx.game_map.snake_map[x][y] != -1:
            return False
        # check other snake
        return True

    def check_self(self, op):
        """
        :param op: the direction
        :return: True if this move is legal, could possibly result in solidification.
                 False otherwise.
        """
        x = self.snake.coor_list[0][0] + dx[op]
        y = self.snake.coor_list[0][1] + dy[op]
        if x < 0 or y < 0 or x >= 16 or y >= 16 or self.ctx.game_map.wall_map[x][y] != -1:
            return False
        if self.snake.get_len() > 1 and x == self.snake.coor_list[1][0] and y == self.snake.coor_list[1][1]:
            return False
        if self.ctx.game_map.snake_map[x][y] != -1 and self.ctx.game_map.snake_map[x][y] != self.snake.id:
            return False
        return True

    def closest_food_strategy(self):
        """
        Search for the closest food and to go that direction, if legal.

        :return: the chosen direction
        """
        def calc_dist(x1, y1, x2, y2):
            """
            Calculate the Manhattan distance between snake head and item.
            And find the possible direction to the item, at most 2.

            :return: (dist, possible_direction)
            """
            pos = []
            if x1 > x2:
                pos.append(0)
            if x1 < x2:
                pos.append(2)
            if y1 > y2:
                pos.append(1)
            if y1 < y2:
                pos.append(3)
            return abs(x1 - x2) + abs(y1 - y2), pos

        valid = []
        for i in range(4):
            if self.check(i):
                valid.append(i)
        if len(valid) == 0:
            if self.snake.get_len() > 1 and self.snake.coor_list[0][0] + dx[0] == self.snake.coor_list[1][0] and self.snake.coor_list[0][1] + dy[0] == self.snake.coor_list[1][1]:
                return 1
            return 0
        # calculate the legal moves without concerning the food

        coor = self.snake.coor_list
        dist, val = INF, []
        for item in self.ctx.game_map.item_list:
            if item.type != 0:
                continue
            # search food only

            if item.time > self.ctx.turn + SEARCH_LIMIT or item.time + item.param < self.ctx.turn:
                continue
            # search valid food only

            d, pos = calc_dist(item.x, item.y, coor[0][0], coor[0][1])
            pos = [i for i in pos if i in valid]
            # use legal move only

            if len(pos) > 0 and d < dist and \
                    d + self.ctx.turn <= item.time + item.param <= d + self.ctx.turn + SPLIT_LIMIT / 2:
                dist, val = d, pos
            # search reachable food only
            # not that the span of a snake is at least SPLIT_LIMIT / 2

        # chose the closest reachable food and use legal move

        if len(val) == 0:
            val = valid
        i = random.randint(0, len(val) - 1)
        # randomly chose one if multiple available

        return val[i]

    def active_strategy(self):
        """
        Strategy for the active snake. Split whenever limit is reached.
        Fire whenever possible. Otherwise search for food.
        """
        if len(self.snake.coor_list) >= SPLIT_LIMIT:
            return 6
        elif len(self.snake.item_list) > 0 and len(self.snake.coor_list) > 1:
            return 5
        else:
            return self.closest_food_strategy() + 1

    def solidify_strategy(self):
        """
        Try to solidify self by forming a 2 * 2 area.
        It requires at most 4 move to solidify.

        :return: direction to move
        """
        if self.snake.id in self.order:
            rk, order = self.order[self.snake.id]
            self.order[self.snake.id] = rk + 1, order
            return order[rk] % 4
            # not the first move, follow the previous move
        else:
            for i in range(4):
                if self.check_self(i):
                    order = [i, i + 1, i + 2, i + 3]
                    self.order.update({self.snake.id: (1, order)})
                    return i % 4
            # the first move, choose a legal direction at store it in self.order
            return 0

    def passive_strategy(self):
        """
        Strategy for other snake. Always solidify.
        """
        return self.solidify_strategy() + 1

    def judge(self, snake, ctx):
        """
        :param snake: current snake
        :param ctx: current context
        :return: the decision
        """
        self.ctx = ctx
        self.snake = snake
        if snake.id == 0 or snake.id == 1:
            return self.active_strategy()
        else:
            return self.passive_strategy()


def run():
    """
    This function maintains the context, i.e. simulating the game.
    It is not necessary to understand this function for you to write an AI.
    """
    c = Client()
    # game config
    (length, width, max_round, player) = c.fetch_data()
    config = GameConfig(width=width, length=length, max_round=max_round)
    ctx = Context(config=config)
    current_player = 0

    logging.info('Assigned player %d', player)

    # read items
    item_list = c.fetch_data()
    ctx.game_map = Map(item_list, config=config)
    controller = Controller(ctx)
    # read & write operations
    playing = True
    ai = AI()
    while playing:
        if controller.ctx.turn > max_round:
            res = c.fetch_data()
            sys.stderr.write(str(res[1:]))
            break
        if current_player == 0:
            controller.round_preprocess()
        controller.round_init()
        if player == current_player:  # Your Turn
            while controller.next_snake != -1:
                current_snake = controller.current_snake_list[controller.next_snake][0]
                op = ai.judge(current_snake, controller.ctx)  # TODO: Complete the Judge Function
                logging.debug(str(op))
                if not controller.apply(op):
                    raise RuntimeError("Illegal Action!!! " + str(op))
                c.send_data(op)
                res = c.fetch_data()
                if res[0] == -1:
                    playing = False
                    sys.stderr.write(str(res[1:]))
                    break
            controller.next_player()
        else:
            while True:
                if controller.next_snake == -1:
                    controller.next_player()
                    break
                op = c.fetch_data()
                if op[0] == -1:
                    playing = False
                    sys.stderr.write(str(op[1:]))
                    break
                controller.apply(op[0])
        current_player = 1 - current_player
    while True:
        pass
