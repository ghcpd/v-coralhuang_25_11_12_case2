// app.js - fixed logic to prevent DOM flicker, overlapping, and distorted media
const chat = document.getElementById('chat');
const messages = document.getElementById('messages');
const btn = document.getElementById('simulate');
const insertBtn = document.getElementById('insertOnce');
let msgCounter = messages.children.length;
let headerCounter = 1;

function isAtBottom(container) {
  return Math.abs(container.scrollHeight - container.scrollTop - container.clientHeight) < 5;
}

function preserveScrollOnAppend(container, fn) {
  const wasAtBottom = isAtBottom(container);
  const prevScroll = container.scrollTop;
  const prevHeight = container.scrollHeight;
  fn();
  // small delay to wait for layout
  requestAnimationFrame(() => {
    const delta = container.scrollHeight - prevHeight;
    if (wasAtBottom) {
      container.scrollTop = container.scrollHeight - container.clientHeight;
    } else {
      container.scrollTop = prevScroll + delta;
    }
  });
}

function createMessage({side='left', text='', mediaSrc=null, avatar='assets/avatars/avatar1.svg'}) {
  msgCounter++;
  const el = document.createElement('div');
  el.className = `message message-${side}`;
  el.setAttribute('data-id', `m${msgCounter}`);
  // avatar
  const avatarImg = document.createElement('img');
  avatarImg.className = 'avatar';
  avatarImg.src = avatar;
  avatarImg.alt = 'User avatar';
  el.appendChild(avatarImg);
  // content
  if (mediaSrc) {
    const img = document.createElement('img');
    img.className = 'media';
    img.alt = 'Image';
    img.src = mediaSrc;
    // ensure no forced rotation
    img.style.transform = '';
    // ensure client dims match natural
    img.onload = () => {
      // cap rendering width to avoid layout overflow but maintain aspect ratio
      const maxW = 240;
      if (img.naturalWidth && img.naturalHeight) {
        if (img.naturalWidth > maxW) {
          img.style.width = maxW + 'px';
        } else {
          img.style.width = img.naturalWidth + 'px';
        }
        img.style.height = 'auto';
      }
    }
    el.appendChild(img);
  } else {
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text || 'New message';
    el.appendChild(bubble);
  }
  return el;
}

function addMessageAtBottom(options) {
  preserveScrollOnAppend(chat, () => {
    const node = createMessage(options);
    messages.appendChild(node);
  });
}

function updateHeader(timeText) {
  const header = document.querySelector('.time-header');
  if (header) {
    header.innerText = timeText;
  } else {
    const h = document.createElement('div');
    h.className = 'time-header';
    h.id = `time-header-0`;
    h.setAttribute('role','separator');
    h.innerText = timeText;
    chat.insertBefore(h, chat.firstChild);
  }
}

function simulateInsert() {
  // preserve scroll as we insert new headers on top
  const prevScroll = chat.scrollTop;
  const prevHeight = chat.scrollHeight;
  // insert header and a message
  const timeText = `09:${String(Math.floor(Math.random() * 60)).padStart(2,'0')} AM`;
  updateHeader(timeText);
  const side = Math.random() > 0.5 ? 'left' : 'right';
  const media = Math.random() > 0.5 ? 'assets/media/tall1.jpg' : null;
  const avatar = `assets/avatars/avatar${(Math.floor(Math.random()*4)+1)}.svg`;
  const newMsg = createMessage({side, text:'Simulated message', mediaSrc:media, avatar});
  // insert at top of messages list to mimic new incoming older messages
  messages.insertBefore(newMsg, messages.firstChild);
  // adjust scroll to keep user's view in place
  requestAnimationFrame(()=>{
    const delta = chat.scrollHeight - prevHeight;
    chat.scrollTop = prevScroll + delta;
  })
}

btn.addEventListener('click', ()=>{
  // fast scroll simulation using rAF
  let i = 0;
  const ticks = 16;
  function tick() {
    chat.scrollTop = (i % 2 === 0) ? chat.scrollHeight : 0;
    i++;
    if (i < ticks) requestAnimationFrame(tick);
    else {
      // after the animation, insert many messages with minimal DOM churn
      for (let n=0; n<3; n++) {
        addMessageAtBottom({side:Math.random()>0.5?'left':'right', text:'Auto appended message ' + n, mediaSrc: Math.random()>0.75? 'assets/media/tall1.jpg' : null, avatar: `assets/avatars/avatar${(Math.floor(Math.random()*4)+1)}.svg`});
      }
    }
  }
  tick();
});

insertBtn.addEventListener('click', ()=>{
  simulateInsert();
});

// helper for test to call once from browser
window.simulateInsertOnce = simulateInsert;

// Accessibility fixes: ensure unique IDs and add roles
(function ensureUniqueIDs(){
  const ids = new Set();
  document.querySelectorAll('[id]').forEach(e=>{
    if (ids.has(e.id)) {
      // rename to unique
      const newId = e.id + '-' + Math.floor(Math.random()*10000);
      e.id = newId;
    }
    ids.add(e.id);
  });
})();

// Prevent overlap by ensuring no absolute positions remain
(function checkForAbsolute(){
  const abs = document.querySelectorAll('.message');
  abs.forEach(m=>{
    m.style.position = 'relative';
  })
})();
