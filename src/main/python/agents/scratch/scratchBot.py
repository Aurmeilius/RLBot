import math
from agents.scratch import socketServer

from RLBotFramework.agents.base_flatbuffer_agent import BaseFlatbufferAgent
from RLBotFramework.agents.base_flatbuffer_agent import SimpleControllerState
from RLBotMessages.flat import GameTickPacket


class FlatBot(BaseFlatbufferAgent):

    def __init__(self, name, team, index):
        BaseFlatbufferAgent.__init__(self, name, team, index)
        self.scratch = socketServer.SocketServer()
        self.scratch.connect()
        self.persistent_controller = SimpleControllerState()

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:

        try:
            scratch_state = self.scratch.fetchControllerState()
        except ConnectionResetError as e:
            self.logger.error(str(e))
            self.scratch.destroy()
            self.scratch = socketServer.SocketServer()
            return self.persistent_controller

        if scratch_state is not None:
            self.persistent_controller.steer = scratch_state['steer']
            self.persistent_controller.throttle = scratch_state['throttle']
            self.persistent_controller.pitch = scratch_state['pitch']
            self.persistent_controller.yaw = scratch_state['yaw']
            self.persistent_controller.roll = scratch_state['roll']
            self.persistent_controller.jump = scratch_state['jump']
            self.persistent_controller.boost = scratch_state['boost']
            self.persistent_controller.handbrake = scratch_state['handbrake']

        if packet.Ball() is None:  # This happens during replays
            return self.persistent_controller

        ball_phys = packet.Ball().Physics()

        ball_location = Vector2(ball_phys.Location().X(), ball_phys.Location().Y())

        my_car = packet.Players(self.index)
        car_location = Vector2(my_car.Physics().Location().X(), my_car.Physics().Location().Y())
        car_direction = get_car_facing_vector(my_car)
        car_to_ball = ball_location - car_location

        steer_correction_radians = car_direction.correction_to(car_to_ball)

        players = []
        for i in range(packet.PlayersLength()):
            players.append(playerToDict(packet.Players(i)))

        self.scratch.sendGameTickData({
            'ball': {
                'location': v3ToDict(ball_phys.Location()),
                'velocity': v3ToDict(ball_phys.Velocity())
            },
            'players': players
        })

        return self.persistent_controller

def playerToDict(car):
    return {
        'location': v3ToDict(car.Physics().Location()),
        'velocity': v3ToDict(car.Physics().Velocity()),
        'rotation': rotToDict(car.Physics().Rotation())
    }

def v3ToDict(v3):
    return {
        'x': v3.X(),
        'y': v3.Y(),
        'z': v3.Z()
    }

def rotToDict(rot):
    return {
        'pitch': rot.Pitch(),
        'yaw': rot.Yaw(),
        'roll': rot.Roll()
    }

class Vector2:
    def __init__(self, x=0, y=0):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, val):
        return Vector2(self.x + val.x, self.y + val.y)

    def __sub__(self, val):
        return Vector2(self.x - val.x, self.y - val.y)

    def __str__(self):
        return '({:0.2f}, {:0.2f})'.format(self.x, self.y)

    def correction_to(self, ideal):
        # The in-game axes are left handed, so use -x
        current_in_radians = math.atan2(self.y, -self.x)
        ideal_in_radians = math.atan2(ideal.y, -ideal.x)

        correction = ideal_in_radians - current_in_radians

        # Make sure we go the 'short way'
        if abs(correction) > math.pi:
            if correction < 0:
                correction += 2 * math.pi
            else:
                correction -= 2 * math.pi

        return correction


def get_car_facing_vector(car):
    pitch = car.Physics().Rotation().Pitch()
    yaw = car.Physics().Rotation().Yaw()

    facing_x = math.cos(pitch) * math.cos(yaw)
    facing_y = math.cos(pitch) * math.sin(yaw)

    return Vector2(facing_x, facing_y)
