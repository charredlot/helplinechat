
var g_state = {}

post_message = function(path, data) {
    var xhr = new XMLHttpRequest();
    
    xhr.open('POST', path, true);
    xhr.setRequestHeader("Content-type","application/x-www-form-urlencoded");
    xhr.send('data=' + JSON.stringify(data));  
}

onOpened = function() {
    var data = {}
    
    data['room_name'] = g_state.room_name;
    
    post_message("/channel/opened", data);
};

onMessage = function(m) {
    var msg = JSON.parse(m.data);
    
    if ('is_server' in msg) {
        line = "<br><b>" + msg.line + "</b>";
    } else {
        line = "<br><b>" + msg.from + "</b>: " + msg.line;
    }
    
    var lines = $('#lines')
    
    lines.append(line);
    lines.scrollTop(lines[0].scrollHeight);
    // $('#lines').append($('<br>').append($('<b>').text(msg.from), msg.line));
};

openChannel = function(room_name, tok) {
    g_state.room_name = room_name;
    var token = tok;
    var channel = new goog.appengine.Channel(token);
    var handler = {
      'onopen': onOpened,
      'onmessage': onMessage,
      'onerror': function() {},
      'onclose': function() {}
    };
    var socket = channel.open(handler);
    socket.onopen = onOpened;
    socket.onmessage = onMessage;
}

initialize = function(room_name, token) {
    openChannel(room_name, token);
};

send_to_room = function() {
    var data = {}
    
    data.room_name = g_state.room_name;
    data.line = $("#chatmsg").val();
    
    post_message("/channel/msg", data);
    $("#chatmsg").val("");
}



