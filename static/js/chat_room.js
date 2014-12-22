
var g_state = {};

var post_message = function(path, data) {
    var xhr = new XMLHttpRequest();
    
    xhr.open('POST', path, true);
    xhr.setRequestHeader("Content-type","application/x-www-form-urlencoded");
    xhr.send('data=' + JSON.stringify(data));  
};

var bad_num_to_str = function(num) {
    if (num < 10) {
        return '0' + num;
    } else {
        return String(num);
    }
};

onOpened = function() {
    var data = {};    
    
    $("#status").html("<b>Connected</b>");
    
    data['room_name'] = g_state.room_name;        
    
    post_message("/room/connected", data);
};

var displayUsers = function(msg) {
    var users = msg['users'];
    var chatusers = $("#chatusers");
    
    for (var i=0, size=users.length; i < size; i++) {
        var l = "<br><b>" + users[i] + "</b>";
        
        chatusers.append(l);
    }
}

onMessage = function(m) {
    var msg = JSON.parse(m.data);
    var d = new Date()
    
    line = "<br><b>&lt;" +
        bad_num_to_str(d.getHours()) + ':' +
        bad_num_to_str(d.getMinutes()) + ':' +
        bad_num_to_str(d.getSeconds()) + 
        "&gt;</b> ";
        
    var content = msg['content'];
    
    if (content === 'user_list') {
        displayUsers(msg);
        return;
    } else if (content === 'announcement') {
        line = line + "<b>" + msg.line + "</b>";
    } else if (content === 'user_msg') {
        line = line + "<b>" + msg.from + "</b>: " + msg.line;
    }
    
    var lines = $('#chatlines');
    
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
    
    data['room_name'] = g_state.room_name;
    data['line'] = $("#chatmsg").val();
    
    post_message("/room/msg", data);
    $("#chatmsg").val("");
}



