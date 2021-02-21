"use strict"
const roomName = JSON.parse(document.querySelector('#room_name').textContent);

const gameChatSocket = new WebSocket(
    'ws://'
    + window.location.host
    + '/game/room/'
    + roomName
    + '/'
);



// set a global variable for opponent username
// keys for later json data
let opponent_user_name = ''
let me_ready = false
let opponent_ready = false
let hasStart = false
let sum = 0

gameChatSocket.onmessage = function (e) {
    // store current acount username in user_name
    let user_name = $("#user_account_name").val()
    const data = JSON.parse(e.data);
    if (data.hasOwnProperty('message')) {
        // if websocket data contains key 'message', it is a chat message
        let strs = data.message.split(":")
        let profileLink = PROFILE_URL.replace('dummy', strs[0])
        let record = "<p class=\"text-left\"><a href=\"" + profileLink +
            "\">" + strs[0] + "</a>:" + strs[1] + "</p>"

        $("#chat-log").append(record)
    } else if (data.hasOwnProperty('player')) { // when enter the room or reconnect
        // if websocket data contains key 'player', it sends data contains player name
        /* {
            'player': {
                'username_host': {
                     'username': ,
                    'pid': ,
                    'score': ,
                    'win': ,
                    'lose': ,
                    'ready': ,
                    'current_draw': ,
                },
                'username_player': {
                    ...
                }
            }
        }
        it iterate through the keys, if the key it is current username,
        it is opponent' username 
        */
        let keys = Object.keys(data.player);
        for (let i = 0; i < keys.length; i++) {
            if (keys[i] === user_name) {
                let userinfo = data.player[user_name]
                if (userinfo.ready) {
                    $("#game-ready").addClass("disabled")
                    me_ready = true
                }
            }

            if (keys[i] != user_name) {  // handle opponnet info
                opponent_user_name = keys[i];
                let info = data.player[opponent_user_name];

                setTimeout(function () {
                    $("#opponent-profile-div").empty()
                    updateOpponent(info.username, info.pid,
                        info.score, info.win,
                        info.lose);

                    if (!opponent_ready && info.ready) {
                        $("#id_button_area_2").append(
                            "<img class='ready-icon'" +
                            " src=\"" + DJANGO_STATIC_URL + "ready.png\" >"
                        )
                        opponent_ready = true

                        if (me_ready && opponent_ready && !hasStart) {
                            gameStart()
                            hasStart = true
                            if (info.current_draw === user_name && sum <= 21) {
                                $("#game-draw").removeClass("disabled")
                                $("#game-draw").prop("disabled", false)
                            }
                        }
                    }
                }, 1500)

            }
        }
        // clear fields if opponent leaves
    } else if (data.hasOwnProperty('ready')) {  // when either user ready
        // if opponent ready
        if (data.ready.username === opponent_user_name && opponent_user_name != '') {
            $("#id_button_area_2").append(
                "<img class='ready-icon'" +
                " src=\"" + DJANGO_STATIC_URL + "ready.png\" >"
            )
            opponent_ready = true
        }

        if (me_ready && opponent_ready && !hasStart) {
            gameStart()
            hasStart = true
        }
    } else if (data.hasOwnProperty('next')) {
        if (data.next === user_name && sum <= 21) {
            $("#game-draw").removeClass("disabled")
            $("#game-draw").prop("disabled", false)
        }
    } else if (data.hasOwnProperty('disconnect')) { // if opponent disconnect
        $("#opponent-profile-div").empty();
        opponent_user_name = ''
        opponent_ready = false
    } else if (data.hasOwnProperty('card')) {
        /* { 
            'card': {
                'username_1': card,
                'username_2': card
            }
        } */
        let keys = Object.keys(data.card)
        for (let i = 0; i < keys.length; i++) {
            if (keys[i] == user_name) {
                addMyCards(data.card[keys[i]], "my-cards", -1);
            } else {
                addMyCards(data.card[keys[i]], "opponent-cards", -1);
            }
        }

    } else if (data.hasOwnProperty('result')) { // when game ends
        /*
        {
            'result' : {
                'user_name1': {
                    result: (win / lose / tie),
                    score:
                    win:
                    lose:
                },
                'user_name2': {...},
                'firstcard': {
                    'user_name1': used_cards,
                    'user_name2': used_cards
                }
            }
        }
        */
        // present result
        let result = data.result[user_name]['result']
        $("#id_result_div").append(
            "<img class='result-img'" +
            " src=\"" + DJANGO_STATIC_URL + result + ".png\" >"
        )

        // update status
        $("#id_my_score").html(data.result[user_name]['score'])
        $('#id_my_win').html(data.result[user_name]['win'])
        $("#id_my_lose").html(data.result[user_name]['lose'])

        $("#id_other_score").html(data.result[opponent_user_name]['score'])
        $('#id_other_win').html(data.result[opponent_user_name]['win'])
        $("#id_other_lose").html(data.result[opponent_user_name]['lose'])

        // show opponent cards
        $("#opponent-cards img:nth-child(2)").remove()

        addMyCards(data.result.firstcard[opponent_user_name], "opponent-cards", 0)

        // add ready btn for next game
        $("#id_draw_div").remove()
        $("#id_show_div").remove()
        let readybtn = "<div id=\"id_ready_div\" class=\"col-sm-2\">\n" +
            "                            <button id=\"game-ready\" class=\"btn btn-default\" onclick=\"gameReady()\"\n" +
            "                                style=\"margin-top: 0px; margin-bottom: 10px\">\n" +
            "                                Ready\n" +
            "                            </button>\n" +
            "                        </div>"
        $("#id_first_row").append(readybtn)

        // reset state
        me_ready = false
        opponent_ready = false
        hasStart = false
        sum = 0
    }
};

gameChatSocket.onclose = function (e) {
    alert('Game room closed unexpectedly. Please try another room.');
    window.location.pathname = '/game/'
};

function sendChatMessageClick() {
    const messageInputDom = document.querySelector('#chat-message-input');
    const user_name = document.querySelector('#user_real_name').value;
    const message = messageInputDom.value;
    gameChatSocket.send(JSON.stringify({
        'message': user_name + ": " + message
    }));
    messageInputDom.value = '';
}


// Update opponents profile, called after enter the room or refresh
function updateOpponent(username, pid, score, win, lose) {
    let url = PHOTO_URL.replace('1', pid)
    let opponent_profile = "<div class=\"row\">" +
        "                <div id=\"id_opponent_img\" class=\"col-sm-offset-2 col-sm-1\">" +
        "                   <img class=\"link_user_picture img-circle\" src=\"" + url + "\" >" +
        "                </div>" +
        "                <div class=\"col-sm-6\">" +
        "                    <div class=\"row\">" +
        "                        <div class=\"form-inline\">" +
        "                            <label class=\"control-label col-sm-1\">Score: </label>" +
        "                            <label id='id_other_score' class=\"control-label col-sm-1\">" + score + "</label>" +
        "                        </div>" +
        "                        <div id=\"id_button_area_2\" class=\"col-sm-2\">" +
        "                        </div>" +
        "                    </div>" +
        "                    <div class=\"row\">" +
        "                        <div class=\"form-inline\">" +
        "                            <label class=\"control-label col-sm-1\">Win: </label>" +
        "                            <label id='id_other_win' class=\"control-label col-sm-1\">" + win + "</label>" +
        "                        </div>" +
        "                        <div class=\"form-inline\">" +
        "                            <label class=\"control-label col-sm-1\">Lose: </label>" +
        "                            <label id='id_other_lose' class=\"control-label col-sm-1\">" + lose + "</label>" +
        "                        </div>" +
        "                    </div>" +
        "                </div>" +
        "            </div>"
    $("#opponent-profile-div").append(opponent_profile)
}

// Add cards to my card board or opponets card board.
// Divname to specify which board to put the card.
// Insert to the front if pos specified as 0, to the back if -1.
function addMyCards(card, divName, pos) {
    let strs = card.split(" ");
    let num = strs[0];
    let type = strs[1];

    // add points of my cards
    if (divName == "my-cards") {
        if (parseInt(num) > 10) {
            sum += 10
        } else {
            sum += parseInt(num)
        }
    }
    if (sum > 21) { // if exceed disable the draw btn
        $("#game-draw").addClass("disabled")
        $("#game-draw").prop("disabled", true)
    }

    // add padding
    if ($("#" + divName).children().length == 0) {
        let interval = " <div class=\"col-sm-1\">" +
            "                </div>"
        $("#" + divName).append(interval)
    }
    let cardName = type + "-" + num + ".jpg";
    let newCard;
    // hide first card on the opponents' deck
    if (divName === "opponent-cards" && $("#" + divName).children().length == 1) {
        newCard = "<img src=\"" + CARD_STATIC_URL
            + "blue-card.png" + "\" class=\"col-sm-2 cards img-rounded\">"
    } else {
        newCard = "<img src=\"" + CARD_STATIC_URL
            + cardName + "\" class=\"col-sm-2 cards img-rounded\">"
    }
    if (pos == -1) {
        $("#" + divName).append(newCard)
    } else if (pos == 0) {
        $("#" + divName + " img:nth-child(2)").before(newCard)
    }
}

// Change UI when game starts
function gameStart() {
    $("#id_button_area_2").empty()
    $("#id_ready_div").remove()
    let drawBtn = "<div id='id_draw_div' class='col-sm-2'>" +
        "<button id=\"game-draw\" class=\"btn btn-default disabled\" onclick=\"gameDrawCard()\"\n" +
        "                                style=\"margin-top: 0px; margin-bottom: 10px\">\n" +
        "                                Draw\n" +
        "                            </button>" +
        "</div>"
    let showBtn = "<div id='id_show_div' class='col-sm-2'>" +
        "<button id=\"game-show\" class=\"btn btn-default\" onclick=\"gameShowCard()\"\n" +
        "                                style=\"margin-top: 0px; margin-bottom: 10px\">\n" +
        "                                Show\n" +
        "                            </button>" +
        "</div>"
    $("#id_first_row").append(drawBtn);
    $("#id_first_row").append(showBtn);

}

// Change UI when user ready
function gameReady() {
    const user_name = document.querySelector('#user_account_name').value;
    gameChatSocket.send(JSON.stringify({
        'ready': user_name
    }));
    // clear previous state
    $("#my-cards").empty()
    $("#opponent-cards").empty()
    $("#id_result_div").empty()

    // disable ready btn
    $("#game-ready").addClass("disabled")
    // update ready status
    me_ready = true

    if (me_ready && opponent_ready && !hasStart) {
        gameStart()
        hasStart = true
    }
}

function gameDrawCard() {
    let user_name = $('#user_account_name').val()
    gameChatSocket.send(JSON.stringify({
        'draw': user_name
    }));
    $("#game-draw").addClass("disabled")
    $("#game-draw").prop("disabled", true)
}

function gameShowCard() {
    const user_name = document.querySelector('#user_account_name').value;
    gameChatSocket.send(JSON.stringify({
        'show': user_name
    }));

    $("#game-show").addClass("disabled")
    $("#game-show").prop("disabled", true)

    $("#game-draw").addClass("disabled")
    $("#game-draw").prop("disabled", true)
}

function getCSRFToken() {
    let cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
        let c = cookies[i].trim();
        if (c.startsWith("csrftoken=")) {
            return c.substring("csrftoken=".length, c.length);
        }
    }
    return "unknown";
}