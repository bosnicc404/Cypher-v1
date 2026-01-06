let chatHistory = [];
let isRecording = false;
let lastInputWasVoice = false;

//voice output
async function speak(text){
    try {
        await fetch('http://127.0.0.1:5000/speak', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({text})
        });
    } catch(e){console.error("TTS failed", e);}
}

//mic toggle
const micBtn = document.getElementById('micBtn');
micBtn.onclick = async ()=>{
    if(isRecording){
        // stop recording
        isRecording=false;
        micBtn.classList.remove('recording');
        micBtn.innerHTML='<i class="fas fa-microphone"></i>';
        lastInputWasVoice=true;
        try{
            const res=await fetch('http://127.0.0.1:5000/whisper_stop',{method:'POST'});
            const data=await res.json();
            if(data.text){
                document.getElementById('userInput').value=data.text;
                document.getElementById('jarvisForm').dispatchEvent(new Event('submit'));
            }
        }catch(e){console.error("Whisper stop failed",e);}
    } else {
        // start recording
        isRecording=true;
        micBtn.classList.add('recording');
        micBtn.innerHTML='<i class="fas fa-circle-notch fa-spin"></i>';
        try{
            await fetch('http://127.0.0.1:5000/whisper_start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
        }catch(e){console.error("Whisper start failed",e);}
    }
};

//chat
document.getElementById('jarvisForm').addEventListener('submit',async(e)=>{
    e.preventDefault();
    const input=document.getElementById('userInput').value.trim();
    if(!input)return;

    const chatDisplay=document.getElementById('chatDisplay');

    // User message
    const userDiv=document.createElement('div');
    userDiv.className='message user';
    userDiv.innerHTML=`<div class="message-content">${input}</div>`;
    chatDisplay.appendChild(userDiv);
    document.getElementById('userInput').value='';

    // Thinking
    const thinkDiv=document.createElement('div');
    thinkDiv.className='message cypher thinking';
    thinkDiv.innerHTML=`<div class="message-content">Cypher is thinking...</div>`;
    chatDisplay.appendChild(thinkDiv);
    chatDisplay.scrollTop=chatDisplay.scrollHeight;

    let aiResponse="";

    try{
        const userLower=input.toLowerCase();
        if(["open","launch","run"].some(word=>userLower.includes(word))){
            await fetch('http://127.0.0.1:5000/exec',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:userLower})});
            aiResponse="Command executed, Boss.";
        } else {
            chatHistory.push({role:'user',content:input});
            try{
                const res=await fetch('http://127.0.0.1:8080/api/chat',{
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({model:'cypher',messages:chatHistory,stream:false})
                });
                const data=await res.json();
                aiResponse=data.message?.content || "Ollama didn't respond.";
            }catch{
                aiResponse="Ollama offline, fallback mode.";
            }
        }

        // Display
        chatDisplay.removeChild(thinkDiv);
        const cypherDiv=document.createElement('div');
        cypherDiv.className='message cypher';
        cypherDiv.innerHTML=`<div class="message-content">${marked.parse(aiResponse)}</div>`;
        chatDisplay.appendChild(cypherDiv);
        chatHistory.push({role:'assistant',content:aiResponse});

        if(lastInputWasVoice){await speak(aiResponse);}
        lastInputWasVoice=false;

        Prism.highlightAll();
        chatDisplay.scrollTop=chatDisplay.scrollHeight;
    }catch(err){
        thinkDiv.textContent="something went wrong. check if ollama is hosted.";
        console.error(err);
    }
});

