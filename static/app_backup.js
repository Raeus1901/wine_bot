/****************************************
 * 1) Manage userId in localStorage
 ****************************************/
let userId = localStorage.getItem("wine_userId");
if (!userId) {
  userId = Date.now().toString();
  localStorage.setItem("wine_userId", userId);
}

/****************************************
 * 2) Global Config & References
 ****************************************/
const serverUrl = "http://127.0.0.1:5001"; // Adjust if your server is on a different port or domain
let conversationDiv, optionsDiv, userInput, submitButton, resetButton;
let isFetching = false; // prevents multiple simultaneous calls

window.addEventListener("DOMContentLoaded", () => {
  conversationDiv = document.getElementById("conversation");
  optionsDiv = document.getElementById("options");
  
  userInput = document.getElementById("user-input");
  submitButton = document.getElementById("submit-button");
  resetButton = document.getElementById("reset-button");

  submitButton.addEventListener("click", handleSubmit);
  resetButton.addEventListener("click", resetRecommender);

  // Start the Q&A
  getNextQuestion();
});

/****************************************
 * 3) Helper: Add a message to conversation
 ****************************************/
function addMessage(sender, text) {
  const p = document.createElement("p");
  p.textContent = `${sender}: ${text}`;
  p.classList.add(sender.toLowerCase()); // "ai", "you", or "system"
  conversationDiv.appendChild(p);
  conversationDiv.scrollTop = conversationDiv.scrollHeight;
}

/****************************************
 * UI Control
 ****************************************/
function disableUI() {
  userInput.disabled = true;
  submitButton.disabled = true;
  const allBtns = optionsDiv.querySelectorAll("button");
  allBtns.forEach(btn => (btn.disabled = true));
}
function enableUI() {
  userInput.disabled = false;
  submitButton.disabled = false;
}

/****************************************
 * GET /next_question
 ****************************************/
async function getNextQuestion() {
  if (isFetching) return;
  isFetching = true;
  disableUI();

  try {
    const resp = await fetch(`${serverUrl}/next_question?user_id=${userId}`);
    const data = await resp.json();

    // If there's an error from the server
    if (data.error) {
      addMessage("System", data.error);
    } else {
      // Display the AI's question or text
      addMessage("AI", data.message);
    }

    // Clear old option buttons
    optionsDiv.innerHTML = "";

    // Attempt to parse "Options: Red, White, etc."
    const match = (data.message || "").match(/Options:\s*(.*)/i);
    if (match) {
      const optionsStr = match[1];
      const opts = optionsStr.split(",").map(o => o.trim());
      opts.forEach(opt => {
        const btn = document.createElement("button");
        btn.textContent = opt;
        btn.addEventListener("click", () => {
          addMessage("You", opt);
          sendAnswer(opt);
        });
        optionsDiv.appendChild(btn);
      });
    }

  } catch (err) {
    console.error("Error fetching next question:", err);
    addMessage("System", "Unable to connect to server.");
  } finally {
    isFetching = false;
    enableUI();
  }
}

/****************************************
 * POST /answer
 ****************************************/
async function sendAnswer(answer) {
  if (isFetching) return;
  isFetching = true;
  disableUI();

  try {
    const resp = await fetch(`${serverUrl}/answer?user_id=${userId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer })
    });
    const data = await resp.json();

    // Show the AI's response (could be final recommendation or next question)
    addMessage("AI", data.message);

    // If not done, auto-fetch the next question
    if (!data.done) {
      await getNextQuestion();
    }

  } catch (err) {
    console.error("Error sending answer:", err);
    addMessage("System", "Unable to connect to server.");
  } finally {
    isFetching = false;
    enableUI();
  }
}

/****************************************
 * POST /reset
 ****************************************/
async function resetRecommender() {
  if (isFetching) return;
  isFetching = true;
  disableUI();

  try {
    const resp = await fetch(`${serverUrl}/reset?user_id=${userId}`, {
      method: "POST"
    });
    const data = await resp.json();

    // Clear conversation area & options
    conversationDiv.innerHTML = "";
    optionsDiv.innerHTML = "";
    userInput.value = "";

    // If server says "System: Session reset. Call /next_question to begin again."
    // we can simply display it and then call getNextQuestion().
    if (data.message) {
      addMessage("System", data.message);
    } else {
      addMessage("System", "Session reset. Starting fresh...");
    }

    // Immediately request the first question again
    await getNextQuestion();

  } catch (err) {
    console.error("Error resetting session:", err);
    addMessage("System", "Unable to connect to server.");
  } finally {
    isFetching = false;
    enableUI();
  }
}

/****************************************
 * Handle typed input
 ****************************************/
function handleSubmit() {
  const ans = userInput.value.trim();
  if (ans) {
    addMessage("You", ans);
    userInput.value = "";
    sendAnswer(ans);
  }
}
