let userId = localStorage.getItem("wine_userId");
if (!userId) {
  userId = Date.now().toString();
  localStorage.setItem("wine_userId", userId);
}

const serverUrl = "http://127.0.0.1:5001";
const conversationDiv = document.getElementById("conversation");
const userInput = document.getElementById("user-input");
const submitButton = document.getElementById("submit-button");
const resetButton = document.getElementById("reset-button");

submitButton.addEventListener("click", handleSend);
resetButton.addEventListener("click", handleReset);

// Press Enter to send
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    handleSend();
  }
});

function addMessage(sender, text) {
  const p = document.createElement("p");
  p.textContent = `${sender}: ${text}`;
  p.classList.add(sender.toLowerCase());
  conversationDiv.appendChild(p);
  conversationDiv.scrollTop = conversationDiv.scrollHeight;
}

function addOptionButtons(options) {
  // Remove old buttons
  document.querySelectorAll(".option-button").forEach((btn) => btn.remove());

  options.forEach((opt) => {
    const btn = document.createElement("button");
    btn.classList.add("option-button");
    btn.textContent = opt;
    btn.addEventListener("click", () => {
      addMessage("You", opt);
      sendChat(opt);
    });
    conversationDiv.appendChild(btn);
  });
  
  conversationDiv.scrollTop = conversationDiv.scrollHeight;
}

function handleSend() {
  const text = userInput.value.trim();
  if (!text) return;

  addMessage("You", text);
  userInput.value = "";
  sendChat(text);
}

async function sendChat(text) {
  try {
    const resp = await fetch(`${serverUrl}/conversation?user_id=${userId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });
    const data = await resp.json();

    if (data.error) {
      addMessage("System", data.error);
      return;
    }

    addMessage("AI", data.message);

    if (data.options && data.options.length > 0) {
      addOptionButtons(data.options);
    } else {
      // remove any leftover option-buttons
      document.querySelectorAll(".option-button").forEach((btn) => btn.remove());
    }
  } catch (err) {
    console.error(err);
    addMessage("System", "Error connecting to server.");
  }
}

function handleReset() {
  addMessage("You", "reset");
  sendChat("reset");
}
