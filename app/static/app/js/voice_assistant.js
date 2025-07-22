const micBtn = document.getElementById('mic-btn');
const userCommand = document.getElementById('user-command');

const speak = (text) => {
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = "en-US";
  speechSynthesis.speak(utter);
};

const handleCommand = (command) => {
  command = command.toLowerCase();
  userCommand.textContent = `You said: ${command}`;

  if (command.includes("wikipedia")) {
    const topic = command.replace("wikipedia", "").trim();
    speak(`Searching Wikipedia for ${topic}`);
    window.open(`https://en.wikipedia.org/wiki/${encodeURIComponent(topic)}`, "_blank");
  } else if (command.includes("open youtube")) {
    speak("Opening YouTube");
    window.open("https://youtube.com", "_blank");
  } else if (command.includes("open google")) {
    speak("Opening Google");
    window.open("https://google.com", "_blank");
  } else if (command.includes("open instagram")) {
    speak("Opening Instagram");
    window.open("https://instagram.com", "_blank");
  } else if (command.includes("what can you do")) {
    speak("I can open websites, search Wikipedia, and help you with orders in your account.");
  } else if (command.includes("who are you")) {
    speak("I am Friday, your virtual assistant.");
  } else if (command.includes("time")) {
    const now = new Date();
    speak(`The time is ${now.toLocaleTimeString()}`);
  } else if (command.includes("open my blog")) {
    window.open("https://codehustler.dev", "_blank");
  } else {
    speak("Sorry, I didn't get that.");
  }
};

const startListening = () => {
  const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  recognition.lang = "en-IN";
  recognition.start();

  recognition.onstart = () => {
    userCommand.textContent = "Listening...";
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    handleCommand(transcript);
  };

  recognition.onerror = (event) => {
    speak("There was an error listening to your voice.");
  };
};

micBtn.addEventListener('click', () => {
  startListening();
});
