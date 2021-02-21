import _thread
import copy
import json
import random
import threading
import time

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import User
from django.http import HttpResponse

from game.models import Profile, Room

game_room_ready_user = {}
game_room_used_cards = {}
game_room_start_status = {}
game_room_end_user = {}
game_room_disconnected = {}
game_room_lock = {}
game_room_next = {}
card_types = ['club', 'diamond', 'heart', 'spade']

RECONNECT_THRESHOLD = 5


class ChatConsumer(WebsocketConsumer):

    def connect(self):
        self.room_group_name = 'chatroom'
        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
            }
        )

    # Receive message from room group
    def chat_message(self, event):
        message = event['message']
        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))


class GameConsumer(WebsocketConsumer):
    def connect(self):
        '''
        This function is called when a websocket connection request is sent from browser
        '''

        self.hostReady = False
        self.playerReady = False

        '''parse game room name'''
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = self.room_name
        '''parse current user'''
        self.user = self.scope['user']

        '''Join room group'''
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        '''get current room from database'''
        current_room = Room.objects.filter(name=self.room_group_name).first()
        if not current_room:
            '''create one if not exists'''
            current_room = Room(name=self.room_group_name, host=None, player=None, num_player=0)
            '''initialize game start status to false'''
            game_room_start_status[self.room_group_name] = False
            '''initialize game ready-user to empty dictionary'''
            game_room_ready_user[self.room_group_name] = {}
            '''initialize game ready-to-show-user to empty dictionary'''
            game_room_end_user[self.room_group_name] = {}
            '''initialize game used cards to empty dictionary'''
            game_room_used_cards[self.room_group_name] = {}
            game_room_used_cards[self.room_group_name]['all_cards'] = {}
            game_room_used_cards[self.room_group_name]['first_cards'] = {}
            # init reconnect states
            game_room_disconnected[self.room_group_name] = []
            game_room_lock[self.room_group_name] = threading.Lock()


        # add players
        game_room_lock[self.room_group_name].acquire()
        # if reconnect
        isReconnect = False
        if self.user.username in game_room_disconnected[self.room_group_name]:
            game_room_disconnected[self.room_group_name].remove(self.user.username)
            isReconnect = True
        else:  # new connection
            if current_room.num_player >= 1 and current_room.host == self.user \
                or current_room.num_player == 2 and current_room.player == self.user \
                or current_room.num_player >= 2:
                # reject dup connections or excessive players
                self.close()
            elif not hasattr(current_room, 'host'):
                current_room.host = self.user
                current_room.num_player += 1
                game_room_ready_user[self.room_group_name][self.user.username] = False
                game_room_end_user[self.room_group_name][self.user.username] = False
                # host draws first
                game_room_next[self.room_group_name] = self.user.username
                current_room.save()
            else:  # add player
                current_room.player = self.user
                current_room.num_player += 1
                game_room_ready_user[self.room_group_name][self.user.username] = False
                game_room_end_user[self.room_group_name][self.user.username] = False
                current_room.save()
        game_room_lock[self.room_group_name].release()
        self.accept()


        # broadcast player info
        hostMsg = {
            'username': current_room.host.username,
            'pid': current_room.host.my_profile.id,
            'score': current_room.host.my_profile.score,
            'win': current_room.host.my_profile.num_win,
            'lose': current_room.host.my_profile.num_lose,
            'ready': game_room_ready_user[self.room_group_name][current_room.host.username],
            'current_draw': game_room_next[self.room_group_name],
        }
        playersInfo = {
            'type': 'players_connect',
            current_room.host.username: hostMsg
        }
        if current_room.num_player == 2:
            playerMsg = {
                'username': current_room.player.username,
                'pid': current_room.player.my_profile.id,
                'score': current_room.player.my_profile.score,
                'win': current_room.player.my_profile.num_win,
                'lose': current_room.player.my_profile.num_lose,
                'ready': game_room_ready_user[self.room_group_name][current_room.player.username],
                'current_draw': game_room_next[self.room_group_name],

            }
            playersInfo[current_room.player.username] = playerMsg

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            playersInfo
        )

        # retrieve game progress for reconnect
        user1, user2, user1_card, user2_card = get_all_cards(current_room.name)

        # send cards to front end
        for card in user1_card:
            user_card = {
                user1: card,
            }
            self.send(text_data=json.dumps({
                'card': user_card
            }))
        for card in user2_card:
            user_card = {
                user2: card,
            }
            self.send(text_data=json.dumps({
                'card': user_card
            }))

    def disconnect(self, close_code):
        _thread.start_new_thread(self.disconnet_handler, ())

    def disconnet_handler(self):
        game_room_lock[self.room_group_name].acquire()
        game_room_disconnected[self.room_group_name].append(self.user.username)
        print("User %s disconnect, now disconnected" % self.user.username)
        print(game_room_disconnected[self.room_group_name])
        game_room_lock[self.room_group_name].release()

        time.sleep(RECONNECT_THRESHOLD)  # wait for reconnect

        game_room_lock[self.room_group_name].acquire()
        if self.user.username not in game_room_disconnected[self.room_group_name]:  # if reconnect
            print("User %s reconnect" % self.user.username)
            game_room_lock[self.room_group_name].release()
            return
        game_room_lock[self.room_group_name].release()

        '''Leave room group, clear all the records'''
        current_room = Room.objects.filter(name=self.room_group_name).first()
        room_name = current_room.name
        if game_room_start_status[self.room_group_name]:  # check if game has started
            result = {}
            host = current_room.host
            player = current_room.player
            result['firstcard'] = {}
            result['firstcard'][host.username] = game_room_used_cards[room_name]['first_cards'][host.username]
            result['firstcard'][player.username] = game_room_used_cards[room_name]['first_cards'][player.username]
            result[host.username] = {}
            result[player.username] = {}
            if self.user == host:
                result[host.username]['result'] = 'lose'
                result[player.username]['result'] = 'win'
                host.my_profile.num_lose += 1
                host.my_profile.score -= 1
                host.my_profile.save()
                player.my_profile.num_win += 1
                player.my_profile.score += 2
                player.my_profile.save()

            else:
                result[host.username]['result'] = 'win'
                result[player.username]['result'] = 'lose'
                host.my_profile.num_win += 1
                host.my_profile.score += 2
                host.my_profile.save()
                player.my_profile.num_lose += 1
                player.my_profile.score -= 1
                player.my_profile.save()

            result[host.username]['score'] = host.my_profile.score
            result[host.username]['win'] = host.my_profile.num_win
            result[host.username]['lose'] = host.my_profile.num_lose

            result[player.username]['score'] = player.my_profile.score
            result[player.username]['win'] = player.my_profile.num_win
            result[player.username]['lose'] = player.my_profile.num_lose

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'send_result',
                    'result': result,
                }
            )

        if current_room.num_player == 1:
            print("Room %s deleted" % self.room_group_name)
            '''if room does not have any players, delete it'''
            current_room.delete()
            game_room_end_user.pop(self.room_group_name, None)
            game_room_ready_user.pop(self.room_group_name, None)
            game_room_start_status.pop(self.room_group_name, None)
            game_room_used_cards.pop(self.room_group_name, None)
            game_room_disconnected.pop(self.room_group_name, None)
            game_room_lock.pop(self.room_group_name, None)
            game_room_next.pop(self.room_group_name, None)
        else:
            current_room.num_player -= 1
            print("Player %s left room %s" % (self.user.username, self.room_group_name))
            '''if host leaves, give host to the next player'''
            if current_room.host == self.user:
                current_room.host = current_room.player
            current_room.player = None
            game_room_end_user[self.room_group_name].pop(self.user.username, None)
            game_room_end_user[self.room_group_name][current_room.host.username] = False
            game_room_ready_user[self.room_group_name].pop(self.user.username, None)
            game_room_ready_user[self.room_group_name][current_room.host.username] = False
            game_room_start_status[self.room_group_name] = False
            game_room_used_cards[self.room_group_name] = {}
            game_room_used_cards[self.room_group_name]['all_cards'] = {}
            game_room_used_cards[self.room_group_name]['first_cards'] = {}
            game_room_disconnected[self.room_group_name].remove(self.user.username)
            game_room_next[self.room_group_name] = current_room.host.username
            current_room.save()

        message = {
            'username': self.user.username
        }
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'disconnect_game',
                'disconnect': message,
            }
        )
        '''reset game info'''
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'reset_game',
            }
        )
        '''leave the group'''
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    '''
    Receive message from WebSocket
    message could be:
        1. chat message
        2. game information
            a. ready
            b. draw cards
            c. show cards
    '''

    def receive(self, text_data):
        current_room = Room.objects.filter(name=self.room_group_name).first()
        text_data_json = json.loads(text_data)
        '''dealing with chat message'''
        if 'message' in text_data_json:
            message = text_data_json['message']
            # Send message to room group
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message
                }
            )

        elif 'ready' in text_data_json:
            '''if two users are ready start game'''
            ready_user = text_data_json['ready']
            game_room_ready_user[self.room_group_name][ready_user] = True

            message = {
                'username': ready_user
            }
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'ready_game',
                    'ready': message,
                }
            )
            if current_room.num_player == 2 \
                and game_room_ready_user[self.room_group_name][current_room.host.username] \
                and game_room_ready_user[self.room_group_name][current_room.player.username] \
                    and not game_room_start_status[self.room_group_name]:
                '''reset previous game info before starting a new game'''
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type': 'reset_game',
                    }
                )
                '''start the game'''
                game_room_start_status[self.room_group_name] = True
                self.start_game()

        elif 'draw' in text_data_json:
            '''if one user draws a card'''
            user = text_data_json['draw']

            '''make sure draw the card only when game start and is not ready to show the cards'''
            if game_room_start_status[self.room_group_name] and not game_room_end_user[self.room_group_name][user]:
                '''draw one unused card and send the browser'''
                card = generate_card(self.room_group_name, user)
                user_card = {
                    user: card,
                }
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type': 'send_card',
                        'card': user_card,
                    }
                )

                self.next_turn()
                # send draw signal
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type': 'your_turn',
                        'next': game_room_next[self.room_group_name]
                    }
                )

        else:
            '''if one user decides to show the cards, make sure only works when game started'''
            if game_room_start_status[self.room_group_name]:
                end_user = text_data_json['show']
                game_room_end_user[self.room_group_name][end_user] = True

                '''only if both users decide to show the card, show the cards'''
                if game_room_end_user[self.room_group_name][current_room.host.username] \
                        and game_room_end_user[self.room_group_name][current_room.player.username]:
                    game_room_end_user[self.room_group_name][current_room.host.username] = False
                    game_room_end_user[self.room_group_name][current_room.player.username] = False
                    game_room_ready_user[self.room_group_name][current_room.host.username] = False
                    game_room_ready_user[self.room_group_name][current_room.player.username] = False
                    game_room_start_status[self.room_group_name] = False
                    game_room_next[self.room_group_name] = current_room.host.username
                    '''send card info'''

                    result = determine_winner(self.room_group_name)
                    async_to_sync(self.channel_layer.group_send)(
                        self.room_group_name,
                        {
                            'type': 'send_result',
                            'result': result,
                        }
                    )

                    # reset cards
                    game_room_used_cards[self.room_group_name]['all_cards'] = {}
                    game_room_used_cards[self.room_group_name]['first_cards'] = {}
                else:   # if game not ends
                    self.next_turn()
                    # send draw signal
                    async_to_sync(self.channel_layer.group_send)(
                        self.room_group_name,
                        {
                            'type': 'your_turn',
                            'next': game_room_next[self.room_group_name]
                        }
                    )


    def start_game(self):
        '''intialize used card decks'''
        game_room_used_cards[self.room_group_name] = {}
        game_room_used_cards[self.room_group_name]['all_cards'] = {}
        game_room_used_cards[self.room_group_name]['first_cards'] = {}
        game_users = []
        for user in game_room_ready_user[self.room_group_name]:
            game_users.append(user)

        '''draw cards '''
        user_1_start_card_1 = generate_card(self.room_group_name, game_users[0])
        user_1_start_card_2 = generate_card(self.room_group_name, game_users[0])
        user_2_start_card_1 = generate_card(self.room_group_name, game_users[1])
        user_2_start_card_2 = generate_card(self.room_group_name, game_users[1])

        game_room_used_cards[self.room_group_name]['first_cards'][game_users[0]] = user_1_start_card_1
        game_room_used_cards[self.room_group_name]['first_cards'][game_users[1]] = user_2_start_card_1

        user_cards_1 = {
            game_users[0]: user_1_start_card_1,
            game_users[1]: user_2_start_card_1,
        }

        user_cards_2 = {
            game_users[0]: user_1_start_card_2,
            game_users[1]: user_2_start_card_2,
        }

        '''send card data'''
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'send_card',
                'card': user_cards_1,
            }
        )

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'send_card',
                'card': user_cards_2,
            }
        )

        # send draw signal
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'your_turn',
                'next': game_room_next[self.room_group_name]
            }
        )

    def next_turn(self):
        current_room = Room.objects.filter(name=self.room_group_name).first()
        # next user draw if not already show
        if game_room_next[self.room_group_name] == current_room.host.username \
                and not game_room_end_user[self.room_group_name][current_room.player.username]:
            game_room_next[self.room_group_name] = current_room.player.username
        else:
            game_room_next[self.room_group_name] = current_room.host.username

    def reset_game(self, event):
        self.send(text_data=json.dumps({
            'reset': 'reset',
        }))

    def disconnect_game(self, event):
        username = event['disconnect']
        self.send(text_data=json.dumps({
            'disconnect': username,
        }))

    def ready_game(self, event):
        username = event['ready']
        self.send(text_data=json.dumps({
            'ready': username,
        }))

    def send_result(self, event):
        result = event['result']
        self.send(text_data=json.dumps({
            'result': result,
        }))

    def send_card(self, event):
        cards = event['card']
        self.send(text_data=json.dumps({
            'card': cards,
        }))

    def your_turn(self, event):
        username = event['next']
        self.send(text_data=json.dumps({
            'next': username,
        }))

    def players_connect(self, event):
        info = copy.copy(event)
        del info['type']
        self.send(text_data=json.dumps({
            'player': info
        }))

    # Receive message from room group
    def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))


'''
helper functions for the game
'''


def generate_card(room_name, user):
    card_number = random.randint(1, 13)
    card_type = random.randint(0, 3)
    card_name = str(card_number) + ' ' + card_types[card_type]
    while True:
        if card_name not in game_room_used_cards[room_name]['all_cards']:
            break
        card_number = random.randint(1, 13)
        card_type = random.randint(0, 3)
        card_name = str(card_number) + ' ' + card_types[card_type]
    game_room_used_cards[room_name]['all_cards'][card_name] = user
    return card_name


def get_all_cards(room_name):
    user1 = None
    user2 = None
    user1_card = []
    user2_card = []
    for card in game_room_used_cards[room_name]['all_cards']:
        if user1 is None:
            user1_card.append(card)
            user1 = game_room_used_cards[room_name]['all_cards'][card]
            continue

        if user1 == game_room_used_cards[room_name]['all_cards'][card]:
            user1_card.append(card)
            continue

        if user2 is None:
            user2 = game_room_used_cards[room_name]['all_cards'][card]
        user2_card.append(card)

    return user1, user2, user1_card, user2_card


def determine_winner(room_name):
    user1, user2, user1_card, user2_card = get_all_cards(room_name)

    user1_score = extract_score(user1_card)
    user2_score = extract_score(user2_card)
    result = {}

    user1_id = User.objects.get(username=user1)
    user1_profile = Profile.objects.get(user=user1_id)
    user2_id = User.objects.get(username=user2)
    user2_profile = Profile.objects.get(user=user2_id)

    result[user1] = {}
    result[user2] = {}

    if (user1_score > 21 and user2_score > 21) or (user1_score == user2_score):
        result[user1]['result'] = 'tie'
        result[user2]['result'] = 'tie'
    elif (user1_score > 21 and user2_score < 21) or (user2_score <= 21 and user2_score > user1_score):
        result[user1]['result'] = 'lose'
        result[user2]['result'] = 'win'
        user1_profile.num_lose += 1
        user1_profile.score -= 1
        user2_profile.num_win += 1
        user2_profile.score += 2
    else:
        result[user1]['result'] = 'win'
        result[user2]['result'] = 'lose'
        user1_profile.num_win += 1
        user1_profile.score += 2
        user2_profile.num_lose += 1
        user2_profile.score -= 1

    user1_profile.save()
    user2_profile.save()
    result['firstcard'] = {}
    result['firstcard'][user1] = game_room_used_cards[room_name]['first_cards'][user1]
    result['firstcard'][user2] = game_room_used_cards[room_name]['first_cards'][user2]

    result[user1]['score'] = user1_profile.score
    result[user1]['win'] = user1_profile.num_win
    result[user1]['lose'] = user1_profile.num_lose

    result[user2]['score'] = user2_profile.score
    result[user2]['win'] = user2_profile.num_win
    result[user2]['lose'] = user2_profile.num_lose
    return result


def extract_score(user_card):
    user_score = 0
    for i in range(len(user_card)):
        digits = ""
        for j in user_card[i]:
            if j.isdigit():
                digits += j
        user_score += min(10, int(digits))
    return user_score
