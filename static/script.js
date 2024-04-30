var socket = io(); // Connect to SocketIO

$('#message-form').submit(function(e) {
    e.preventDefault(); 
    var message = $('#message-input').val();
    socket.emit('send_message', message); 
    $('#message-input').val(''); 
    return false; 
});

socket.on('receive_message', function(data) {
    $('#chat-messages').append('<p>' + data + '</p>'); 
});
