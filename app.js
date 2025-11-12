// app.js - stable DOM updates, preserve scroll position, no forced rotation
const chat = document.getElementById('chat');
const btn = document.getElementById('simulate');
let insertedCount = 0;

function preserveScrollFor(action){
  const oldScrollTop = chat.scrollTop;
  const oldScrollHeight = chat.scrollHeight;
  action();
  // compute delta and preserve
  const newScrollHeight = chat.scrollHeight;
  const delta = newScrollHeight - oldScrollHeight;
  // If user is at the very top, avoid nudging scroll; else preserve viewed content position
  if (oldScrollTop > 5) {
    chat.scrollTop = Math.max(0, oldScrollTop + delta);
  }
}

function createTimeHeader(text){
  // create unique ID using timestamp and incremental counter
  const id = 'time-header-' + Date.now() + '-' + (insertedCount++);
  const header = document.createElement('div');
  header.className = 'time-header';
  header.id = id;
  header.setAttribute('role','separator');
  header.innerText = text;
  return header;
}

function createMessage(){
  const side = Math.random() > 0.5 ? 'left' : 'right';
  const msg = document.createElement('div');
  msg.className = `message ${side}`;

  const avatar = document.createElement('img');
  avatar.className = 'avatar';
  avatar.alt = 'random avatar';
  // use static SVG data urls for offline / reproducible tests
  const hue = Math.floor(Math.random() * 360);
  avatar.src = `data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='36' height='36'><rect rx='18' width='36' height='36' fill='%23${Math.abs(hue*12345).toString(16).slice(0,6)}'/></svg>`;

  msg.appendChild(avatar);

  if (Math.random() > 0.5) {
    const img = document.createElement('img');
    img.className = 'media';
    img.alt = 'attached image';
    const w = Math.floor(Math.random() * 200 + 150);
    const h = Math.floor(Math.random() * 400 + 200);
    // create SVG to avoid external network dependencies and preserve aspect ratio
    img.src = `data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}'><rect width='${w}' height='${h}' fill='%23B39DDB'/></svg>`;

    // ensure the rendered size preserves the natural aspect ratio
    img.addEventListener('load', () => {
      try {
        const ar = img.naturalWidth / img.naturalHeight;
        // set CSS aspect-ratio if supported
        if ('aspectRatio' in document.body.style) {
          img.style.aspectRatio = `${img.naturalWidth} / ${img.naturalHeight}`;
        }
        // Make sure image widths respect container
        img.style.maxWidth = '320px';
        img.style.height = 'auto';
        img.style.objectFit = 'cover';
      } catch(e) { console.warn(e) }
    })

    msg.appendChild(img);
  } else {
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = 'Random text message ' + Math.floor(Math.random() * 100);
    msg.appendChild(bubble);
  }

  return msg;
}

function injectNewContent(){
  preserveScrollFor(() => {
    // create header and message; append safely
    const header = createTimeHeader('09:' + String(Math.floor(Math.random() * 60)).padStart(2, '0') + ' AM');
    // If we have multiple headers, keep only last N of them
    const existing = document.querySelectorAll('.time-header');
    if (existing.length > 10) {
      existing[0].remove();
    }
    chat.insertBefore(header, chat.firstChild);

    // append only a message at bottom when explicit; injectNewContent will not append a message when called by tests
  });
}

// Expose a stable simulate function required by tests
window.simulateInsertOnce = function(){
  injectNewContent();
}

btn.addEventListener('click', async () => {
  // simulate fast scrolling while adding an item
  let scrollCount = 0;
  function fastScroll(){
    chat.scrollTop = (scrollCount % 2 === 0) ? chat.scrollHeight : 0;
    scrollCount++;
    if (scrollCount < 20) {
      requestAnimationFrame(fastScroll);
    } else {
      injectNewContent();
    }
  }
  fastScroll();
});
