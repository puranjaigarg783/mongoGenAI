document.addEventListener('DOMContentLoaded', async function () {
    const responseContainer = document.getElementById('mainContainer');
    const inputBox = document.getElementById('inputBox');
    const submitButton = document.getElementById('submitButton');
    const loading = document.getElementById('loading');
  
    const responseData = await SendYoutubeVideoToBackEnd();
    if (responseData) {
        // Make the main container visible
        loading.style.display = 'none';
        responseContainer.style.display = 'block';
    } else {
        console.error('Error fetching data from backend');
    }
  
    submitButton.addEventListener('click', async function () {
        const userInput = inputBox.value;
        if (userInput.trim() !== '') {
            // Make backend call with user input
            const backendResponse = await sendUserInput(userInput);
            console.log(backendResponse);

            if (backendResponse) {
                const llmResponse = backendResponse.llm_output;
                console.log("LLM Response:", llmResponse);
                addChatMessage(llmResponse);
            } else {
                console.error('Error sending user input to backend');
            }
        } else {
            console.error('Please enter something in the input box');
        }
    });
});
  
async function SendYoutubeVideoToBackEnd() {
    // Get active tab information
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
    // Log active tab information
    console.log('Active Tab:', tab.url);

    // Using URL API to parse the URL
    const parsedUrl = new URL(tab.url);

    // Getting different components of the URL
    const protocol = parsedUrl.protocol;
    const hostname = parsedUrl.hostname;
    const path = parsedUrl.pathname;
    const searchParams = parsedUrl.searchParams;

    // Getting specific parameters from the search string
    videoId = searchParams.get('v');

    console.log("Protocol:", protocol);
    console.log("Hostname:", hostname);
    console.log("Path:", path);
    console.log("Video ID:", videoId);
  
    try{
        const response = await fetch('http://127.0.0.1:8001/load', {
            method: 'POST',
            body: JSON.stringify({ video_id : videoId }),
            headers: {
            'Content-Type': 'application/json'
            }
        });
        if (response.ok) {
            const data = await response.json();
            console.log('Backend Response:', data);
            return data;
        } else {
            console.error('Error sending user input to backend:', response.status);
            return null;
        }
    } catch (error) {
        console.error('Error sending user input to backend:', error);
        return null;
    }
}

async function sendUserInput(userInput) {
    try{
        console.log(videoId);
        const response = await fetch('http://127.0.0.1:8001/get_response', {
            method: 'POST',
            body: JSON.stringify({ user_query : userInput, video_id : videoId }),
            headers: {
                'Content-Type': 'application/json'
            }
        });
        if (response.ok) {
            const data = await response.json();
            console.log('Backend Response:', data);
            return data;
        } else {
            console.error('Error sending user input to backend:', response.status);
            return null;
        }
    } catch (error) {
        console.error('Error sending user input to backend:', error);
        return null;
    }
}

function addChatMessage(jsonResponse) {
    var msgPage = document.querySelector(".msg-page");
    if (msgPage) {
        var receivedChats = document.createElement("div");
        receivedChats.classList.add("received-chats");

        var receivedMsg = document.createElement("div");
        receivedMsg.classList.add("received-msg");

        var receivedMsgInbox = document.createElement("div");
        receivedMsgInbox.classList.add("received-msg-inbox");

        var message = document.createElement("p");
        message.textContent = inputBox.value;

        inputBox.value = "";

        var time = document.createElement("span");
        time.classList.add("time");
        time.textContent = getCurrentTime();

        receivedMsgInbox.appendChild(message);
        receivedMsgInbox.appendChild(time);

        receivedMsg.appendChild(receivedMsgInbox);

        receivedChats.appendChild(receivedMsg);

        msgPage.appendChild(receivedChats);

        var outgoingChats = document.createElement("div");
        outgoingChats.classList.add("outgoing-chats");

        var outgoingMsg = document.createElement("div");
        outgoingMsg.classList.add("outgoing-msg");

        var outgoingChatsMsg = document.createElement("div");
        outgoingChatsMsg.classList.add("outgoing-chats-msg");

        var message = document.createElement("p");
        message.textContent = jsonResponse;

        var time = document.createElement("span");
        time.classList.add("time");
        time.textContent = getCurrentTime();

        outgoingChatsMsg.appendChild(message);
        outgoingChatsMsg.appendChild(time);

        outgoingMsg.appendChild(outgoingChatsMsg);

        outgoingChats.appendChild(outgoingMsg);

        msgPage.appendChild(outgoingChats);

        msgPage.scrollTo({
            top: msgPage.scrollHeight,
            behavior: 'smooth'
        });
    } else {
        console.error("Message page container not found.");
    }
}
function getCurrentTime() {
    var now = new Date();
    var hours = now.getHours();
    var minutes = now.getMinutes();
    var ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    minutes = minutes < 10 ? '0' + minutes : minutes;
    var timeString = hours + ':' + minutes + ' ' + ampm;
    return timeString;
}
  