const gameChatSocket = new WebSocket(
    'ws://'
    + window.location.host
    + '/game/'
);

gameChatSocket.onmessage = function (e) {
    const data = JSON.parse(e.data);
    if (data.hasOwnProperty('message')) {
        let strs = data.message.split(":")
        let profileLink = PROFILE_URL.replace('dummy', strs[0])
        let record = "<p class=\"text-left\"><a href=\"" + profileLink +
            "\">" + strs[0] +"</a>:" + strs[1] + "</p>"

        $("#chat-log").append(record)
    }
};

gameChatSocket.onclose = function (e) {
    alert('Game lobby closed unexpectedly. Please reconnect.');
};


function sendChatMessageClick() {
    const messageInputDom = document.querySelector('#chat-message-input');
    // const user_name = document.querySelector('#user_real_name').value;
    const user_name = document.getElementById('id_user_name').value;
    const message = messageInputDom.value;
    gameChatSocket.send(JSON.stringify({
        'message': user_name + ": " + message
    }));
    messageInputDom.value = '';
}

function enterGameRoom() {
    let roomName = document.querySelector('#room-enter-name').value;
    if (roomName == '') {
        alert('The name of the room cannot be empty.');
        return;
    }
    window.location = location.protocol + "//" + location.hostname + ":" + location.port + "/game/room/" + roomName + "/";
}