const socket = io('http://localhost:8000');

socket.on('connect', () => {
    console.log('Connected to the server');
    socket.emit('message', { query: 'How many pending trainings do I have?' });
});

socket.on('chat_response', (response) => {
    console.log('Received response:', response);
});

socket.on('disconnect', () => {
    console.log('Disconnected from the server');
});
