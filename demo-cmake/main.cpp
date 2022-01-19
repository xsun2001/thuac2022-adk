#include "adk.hpp"
#include <cmath>

Operation
make_your_decision( const Snake &snake_to_operate, const Context &ctx )
{
	//若该蛇有道具，执行融化射线操作
	if ( snake_to_operate.railgun_item.id != -1 )
	{
		return OP_RAILGUN;
	}

	//若为该玩家操控的首条蛇且长度超过10且蛇数少于4则分裂
	if ( snake_to_operate == ctx.my_snakes()[0] )
	{
		//若该蛇长度超过10
		if ( snake_to_operate.length() >= 10 )
		{
			//若蛇的数量少于4
			if ( ctx.my_snakes().size() < 4 )
				return OP_SPLIT;
		}
	}

	Operation direction[4] = { OP_RIGHT, OP_UP, OP_LEFT, OP_DOWN };

	int dx[4] = { 1, 0, -1, 0 };
	int dy[4] = { 0, 1, 0, -1 };
	//确定合法移动方向
	//-1代表移动非法，0代表正常移动，1代表移动触发固化
	int move[4] = { 0, 0, 0, 0 };
	for ( int dir = 0; dir < 4; dir++ )
	{
		//蛇头到达位置
		int t_x = snake_to_operate[0].x + dx[dir];
		int t_y = snake_to_operate[0].y + dy[dir];

		//超出边界
		if ( t_x >= ctx.length() || t_x < 0 || t_y >= ctx.width() || t_y < 0 )
		{
			move[dir] = -1;
			continue;
		}

		//撞墙
		if ( ctx.wall_map()[t_x][t_y] != -1 )
		{
			move[dir] = -1;
			continue;
		}

		//撞非本蛇
		if ( ctx.snake_map()[t_x][t_y] != -1 &&
			 ctx.snake_map()[t_x][t_y] != snake_to_operate.id )
		{
			move[dir] = -1;
			continue;
		}

		//回头撞自己
		if ( snake_to_operate.length() > 2 &&
			 snake_to_operate[1].x == t_x &&
			 snake_to_operate[1].y == t_y )
		{
			move[dir] = -1;
			continue;
		}

		//移动导致固化
		if ( ctx.snake_map()[t_x][t_y] == snake_to_operate.id )
		{
			move[dir] = 1;
			continue;
		}
	}

	//玩家操控的首条蛇朝向道具移动
	if ( snake_to_operate == ctx.my_snakes()[0] )
	{
		for ( int i = 0; i < ctx.item_list().size(); i++ )
		{
			//道具已经消失
			if ( ctx.item_list()[i].time + ITEM_EXPIRE_LIMIT < ctx.current_round() )
				continue;

			//计算蛇头与道具的距离
			int distance = abs( ctx.item_list()[i].x - snake_to_operate[0].x ) +
						   abs( ctx.item_list()[i].y - snake_to_operate[0].y );

			//忽略其他因素理论上能吃到该道具
			if ( ctx.item_list()[i].time <= ctx.current_round() + distance &&
				 ctx.item_list()[i].time + 16 > ctx.current_round() + distance )
			{
				for ( int dir = 0; dir < 4; dir++ )
				{
					//移动不合法或固化
					if ( move[dir] != 0 )
						continue;

					//朝向道具方向移动
					int t_x = snake_to_operate[0].x + dx[dir];
					int t_y = snake_to_operate[0].y + dy[dir];
					int dis = abs( ctx.item_list()[i].x - t_x ) + abs( ctx.item_list()[i].y - t_y );
					if ( dis <= distance )
					{
						return direction[dir];
					}
				}
			}
		}
	}

	//其他蛇优先固化，或朝向蛇尾方向移动
	else
	{
		//计算蛇头与蛇尾的距离
		int distance = abs( snake_to_operate.coord_list.back().x - snake_to_operate.coord_list[0].x ) +
					   abs( snake_to_operate.coord_list.back().y - snake_to_operate.coord_list[0].y );
		for ( int dir = 0; dir < 4; dir++ )
		{
			//移动不合法或固化
			if ( move[dir] == -1 )
				continue;

			if ( move[dir] == 1 )
			{
				return direction[dir];
			}

			//朝向蛇尾方向移动
			int t_x = snake_to_operate.coord_list[0].x + dx[dir];
			int t_y = snake_to_operate.coord_list[0].y + dy[dir];
			int dis = abs( snake_to_operate.coord_list.back().x - t_x ) +
					  abs( snake_to_operate.coord_list.back().y - t_y );
			if ( dis <= distance )
			{
				return direction[dir];
			}
		}
	}

	//以上操作均未正常执行，则以如下优先顺序执行该蛇移动方向
	//向空地方向移动>向固化方向移动>向右移动
	for ( int dir = 0; dir < 4; dir++ )
	{
		if ( move[dir] == 0 )
		{
			return direction[dir];
		}
	}
	for ( int dir = 0; dir < 4; dir++ )
	{
		if ( move[dir] == -1 )
		{
			return direction[dir];
		}
	}
	return OP_RIGHT;
}

void game_over( int gameover_type, int winner, int p0_score, int p1_score )
{
	fprintf( stderr, "%d %d %d %d", gameover_type, winner, p0_score, p1_score );
}

int main( int argc, char **argv )
{
	SnakeGoAI start( argc, argv );
}