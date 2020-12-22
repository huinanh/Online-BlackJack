"use strict"

function refreshGameRoom() {
    let request = new XMLHttpRequest()
    request.onreadystatechange = function () {
        if (request.readyState != 4) return
        updateGameRoom(request)
    }
    request.open("GET", "/game/refresh-game-room", true)
    request.send()
}

function refreshScore() {
    let request = new XMLHttpRequest()
    request.onreadystatechange = function () {
        if (request.readyState != 4) return
        updateScore(request)
    }
    request.open("GET", "/game/refresh-score", true)
    request.send()
}

function refreshFriends() {
    let request = new XMLHttpRequest()
    request.onreadystatechange = function () {
        if (request.readyState != 4) return
        updateFriends(request)
    }
    request.open("GET", "/game/refresh-friends", true)
    request.send()
}

function updateScore(request) {
    if (request.status != 200) {
        console.log(request.status)
        return
    }

    let response = JSON.parse(request.responseText)
    $("#scoreboard-list").empty()
    for (let i = 0; i < response.length; i++) {
        let user_data = response[i]
        let record = "<tr>" +
            "                    <td>" + (i + 1) + "</td>" +
            "                    <td>" + user_data.user + "</td>" +
            "                    <td>" + user_data.score + "</td>" +
            "                    <td>" + user_data.win + "</td>" +
            "                    <td>" + user_data.lose + "</td>" +
            "         </tr>"
        $("#scoreboard-list").append(record)
    }
}

function updateGameRoom(request) {
    if (request.status != 200) {
        console.log(request.status)
        return
    }

    let response = JSON.parse(request.responseText)
    let list = document.getElementById("game-room-list")
    list.innerHTML = ''
    for (let i = 0; i < response.length; i++) {
        let game_room_info = response[i]
        let new_room = document.createElement("tr")
        let room_number = document.createElement("td")
        let room_name = document.createElement("td")
        let room_link = document.createElement("a")
        let room_host = document.createElement("td")
        let room_people = document.createElement("td")

        room_number.innerHTML = i + 1

        let link = location.protocol + "//" + location.hostname + ":" + location.port + "/game/room/" + game_room_info.name + "/";
        room_link.setAttribute("href", link)
        room_link.innerHTML = game_room_info.name
        room_name.appendChild(room_link)
        room_host.innerHTML = game_room_info.host
        room_people.setAttribute("id", game_room_info.name)
        room_people.innerHTML = game_room_info.num_player + '/2'

        new_room.appendChild(room_number)
        new_room.appendChild(room_name)
        new_room.appendChild(room_host)
        new_room.appendChild(room_people)
        list.appendChild(new_room)
    }
}

function updateFriends(request) {
    let response = JSON.parse(request.responseText)
    $("#friend-list").empty()
    for (let i = 0; i < response.length; i++) {
        let friend_name = response[i]
        let friend_entry = "<li class=\"list-group-item\">" + friend_name + "&nbsp;" +
            "                    <span class=\"btn btn-default\" " +
            "                           onclick=\"sendInvitation(\'" + friend_name + "\')\">" +
            "                               <i class=\"glyphicon glyphicon-plus\"></i>" +
            "                    </span>" +
            "                </li>"
        $("#friend-list").append(friend_entry)
    }
}

function sendInvitation(friend_name) {
    let req = new XMLHttpRequest()
    req.open("POST", "/game/send-invitation", true);
    req.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    req.send("username=" + friend_name + "&csrfmiddlewaretoken=" + getCSRFToken());
}

function getInvitation() {
    let request = new XMLHttpRequest()
    request.onreadystatechange = function () {
        if (request.readyState != 4) return
        updateInvitation(request)
    }
    request.open("GET", "/game/get-invitation", true)
    request.send()
}

function updateInvitation(request) {
    let response = JSON.parse(request.responseText)
    $('#id_invite_list').empty()
    $("#invitation-badge").html(response.length)
    for (let i = 0; i < response.length; i++) {
        let room_name = response[i].room_name
        let from_username = response[i].from_user

        let invite = "<p>Invitation to " + room_name + " from " + from_username + "&nbsp;" +
            "                                <button class=\"btn btn-default\"" +
            "                                  onclick=\"acceptInvitation('" + room_name + "', '" + from_username + "')\">" +
            "                                    <i class=\"glyphicon gly glyphicon-ok\"></i>\n" +
            "                                </button>\n" +
            "                            </p>"
        $("#id_invite_list").append(invite)
    }
}

function acceptInvitation(room_name, from_username) {
    let req = new XMLHttpRequest()
    req.open("POST", "/game/accept-invitation", true);
    req.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    req.send("username=" + from_username + "&csrfmiddlewaretoken=" + getCSRFToken());

    let link = "/game/room/" + room_name + "/";
    window.location.pathname = link
}

function getCSRFToken() {
    let cookies = document.cookie.split(";")
    for (let i = 0; i < cookies.length; i++) {
        let c = cookies[i].trim()
        if (c.startsWith("csrftoken=")) {
            return c.substring("csrftoken=".length, c.length)
        }
    }
    return "unknown"
}