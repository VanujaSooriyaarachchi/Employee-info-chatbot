const socket = io('http://localhost:8000');

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('chat_response', (data) => {
    console.log('Response from server:', data);
});

function sendMessage(query) {
    socket.emit('message', { query: query });
}

// Example usage
document.getElementById('sendButton').addEventListener('click', () => {
    const query = document.getElementById('queryInput').value;
    sendMessage(query);
});
