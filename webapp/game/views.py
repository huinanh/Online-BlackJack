import json

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.staticfiles.finders import find
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.templatetags.static import static

from game.forms import LoginForm, ProfileForm, RegisterForm
from game.models import Profile, Room


def user_login(request):
    context = {}
    if request.method == 'GET':
        context['form'] = LoginForm()
        return render(request, 'game/login.html', context)

    form = LoginForm(request.POST)
    context['form'] = form

    if not form.is_valid():
        return render(request, 'game/login.html', context)

    user = authenticate(username=form.cleaned_data['username'],
                        password=form.cleaned_data['password'])
    login(request, user)
    return redirect(reverse('home'))


def user_register(request):
    context = {}
    if request.method == 'GET':
        context['form'] = RegisterForm()
        return render(request, 'game/register.html', context)

    form = RegisterForm(request.POST)

    if not form.is_valid():
        context['form'] = form
        return render(request, 'game/register.html', context)

    new_user = User.objects.create_user(username=form.cleaned_data['username'],
                                        password=form.cleaned_data['password'],
                                        email=form.cleaned_data['email'],
                                        first_name=form.cleaned_data['first_name'],
                                        last_name=form.cleaned_data['last_name'])
    new_user.save()
    default_profile = Profile(user=new_user)
    default_profile.gender = form.cleaned_data['gender']
    default_profile.save()
    login(request, new_user)
    return redirect(reverse('home'))


@login_required
def lobby(request):
    context = {'first_name': request.user.first_name, 'last_name': request.user.last_name,
               'username': request.user.username, 'pid': request.user.my_profile.id}

    return render(request, 'game/gameLobby.html', context)


@login_required
def game_room(request, room_name):
    profile = request.user.my_profile
    context = {'first_name': request.user.first_name,
               'last_name': request.user.last_name,
               'username': request.user.username,
               'room_name': room_name,
               'score': profile.score,
               'win': profile.num_win,
               'lose': profile.num_lose,
               'pid': profile.id,
               }

    return render(request, 'game/BlackJackRoom.html', context)


def score_board(request):
    context = {}
    context['first_name'] = request.user.first_name
    context['last_name'] = request.user.last_name
    context['username'] = request.user.username
    context['pid'] = request.user.my_profile.id

    return render(request, 'game/score.html', context)


def refresh_game_room(request):
    response_data = []
    for room in Room.objects.all():
        room_info = {
            'name': room.name,
            'host': room.host.username,
            'num_player': room.num_player,
        }
        response_data.append(room_info)
    response_json = json.dumps(response_data)
    return HttpResponse(response_json, content_type='application/json')


def refresh_score(request):
    response_data = []
    for user_profile in Profile.objects.order_by('-score'):
        user_score = {
            'user': user_profile.user.username,
            'score': user_profile.score,
            'win': user_profile.num_win,
            'lose': user_profile.num_lose,
        }
        response_data.append(user_score)
    response_json = json.dumps(response_data)
    return HttpResponse(response_json, content_type='application/json')


def enter_room(request):
    return render(request, 'game/BlackJackRoom.html', {})

@login_required
def add_room(request):
    if request.method == 'POST':
        if 'roomName' not in request.POST:
            error = {'error': 'Missing required fields'}
            return HttpResponse(json.dumps(error), content_type='application/json')
        roomName = request.POST['roomName']
        if Room.objects.filter(name__exact=roomName).exists():
            error = {'error': 'Duplicate room name!'}
            return HttpResponse(json.dumps(error), content_type='application/json')
        gameRoom = Room(name=roomName, host=request.user)
        gameRoom.save()

        room_item = {
            'id': gameRoom.id,
            'roomName': gameRoom.name,
            'host': request.user.username,
            'playerNum': 1
        }
        return HttpResponse(json.dumps(room_item), content_type='application/json')


@login_required
def get_photo(request, profile_id):
    """
    Fetch photo with profile id
    """
    item = get_object_or_404(Profile, id=profile_id)
    if not item.picture:
        with open(find("game/Rei.jpg"), "rb") as f:
            default_img = f.read()
        return HttpResponse(default_img, content_type="image/jpeg")
    return HttpResponse(item.picture, content_type=item.content_type)


@login_required
def user_profile(request, username):
    profileUser = User.objects.filter(username__exact=username)
    if not profileUser.exists():    # if wrong username, redirect to my profile
        profile = request.user.my_profile
    else:
        profile = profileUser.first().my_profile

    context = {'username': request.user.username,
               'profile_user': username,
               'score': profile.score,
               'win': profile.num_win,
               'lose': profile.num_lose,
               'gender': profile.gender,
               'bio': profile.bio,
               'profile_pid': profile.id,
               'pid': request.user.my_profile.id,
               }

    if request.method == 'GET':
        profileForm = ProfileForm(instance=profile)
        context['form'] = profileForm

    elif request.user.username == username:   # post requests made by myself
        profileForm = ProfileForm(request.POST, request.FILES)
        context['form'] = profileForm
        if not profileForm.is_valid():
            return render(request, 'game/profile.html', context)
        profile.bio = profileForm.cleaned_data['bio']
        context['bio'] = profile.bio
        if request.FILES.__contains__('picture'):   # check if a picture uploaded
            profile.picture.delete(False)
            profile.picture = profileForm.cleaned_data['picture']
            profile.content_type = profileForm.cleaned_data['picture'].content_type

        profile.save()
    else:   # manage friend lists
        if 'follow' in request.POST:
            request.user.my_profile.friends.add(profileUser.first())
        else:
            request.user.my_profile.friends.remove(profileUser.first())

    if request.user.my_profile.friends.filter(username__exact=username).exists():   # check whether a friend
        context['friend'] = True

    return render(request, 'game/profile.html', context)


@login_required
def user_logout(request):
    logout(request)
    return redirect(reverse('login'))


@login_required
@transaction.atomic
def send_invitation(request):
    response = []
    if request.method == 'POST':
        receive_username = request.POST['username']
        receive_user = User.objects.get(username = receive_username)
        receive_user_profile = Profile.objects.get(user = receive_user)
        receive_user_profile.invitations.add(request.user)
        receive_user_profile.save()
        print("%s invite %s" %(request.user.username, receive_user.username))
        response.append("success") 
    else:
        response.append("error") 
    return HttpResponse(json.dumps(response), content_type='application/json')


@login_required
@transaction.atomic
def get_invitation(request):
    user_profile = Profile.objects.get(user=request.user)
    response_data = []
    for invitation in user_profile.invitations.all():
        game_room = Room.objects.filter(host=invitation).first()
        if game_room is not None:
            data = {
                'room_name': game_room.name,
                'from_user': invitation.username,
            }
            response_data.append(data)
    
    response_json = json.dumps(response_data)
    return HttpResponse(response_json, content_type='application/json')


@login_required
def refresh_friends(request):
    print("User %s fetch friend list" % request.user.username)
    user_profile = Profile.objects.get(user=request.user)
    response_data = []
    for friend in user_profile.friends.all():
        response_data.append(friend.username)
    response_json = json.dumps(response_data)
    return HttpResponse(response_json, content_type='application/json')


@login_required
@transaction.atomic
def accept_invitation(request):
    response = []
    if request.method == 'POST':
        accept_username = request.POST['username']
        print("%s accept %s" % (request.user.username, accept_username))
        accept_user = User.objects.get(username = accept_username)
        user_profile = Profile.objects.get(user = request.user)
        user_profile.invitations.remove(accept_user)
        response.append("success")
    else:
        response.append("fail")
    return HttpResponse(json.dumps(response), content_type='application/json')
