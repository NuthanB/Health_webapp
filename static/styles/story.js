const messagesDiv = document.getElementById("messages");
const userInput = document.getElementById("user-input");
const sendButton = document.getElementById("send-button");

function appendMessage(role, content) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", role);
    messageDiv.textContent = content;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

sendButton.addEventListener("click", async () => {
    const userMessage = userInput.value;
    if (!userMessage) return;

    appendMessage("user", userMessage);

    const response = await fetch("/ask", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            user_message: userMessage,
        }),
    });

    const data = await response.json();
    const assistantMessage = data.assistant_message;
    appendMessage("assistant", assistantMessage);

    userInput.value = "";
});
