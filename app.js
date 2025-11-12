(function(){
  const chat = document.getElementById('chat');
  const btn = document.getElementById('simulate');
  let idCounter = 100;

  function generateId(prefix) {
    idCounter += 1;
    return `${prefix}-${idCounter}`;
  }

  function createTimeHeaderLabel() {
    const hh = 9 + Math.floor(Math.random() * 4); // 9-12
    const mm = Math.floor(Math.random() * 60).toString().padStart(2,'0');
    return `${hh}:${mm} AM`;
  }

  function createTimeHeaderNode(label) {
    const header = document.createElement('div');
    header.className = 'time-header';
    header.id = generateId('time');
    header.setAttribute('role','separator');
    header.setAttribute('aria-label', label);
    header.innerText = label;
    return header;
  }

  function createAvatar(color) {
    const img = document.createElement('img');
    img.className = 'avatar';
    const svg = encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' width='40' height='40'><rect width='40' height='40' fill='${color}'/></svg>`);
    img.src = `data:image/svg+xml;utf8,${svg}`;
    img.alt = 'avatar';
    return img;
  }

  function createMediaImage(w,h,color) {
    const img = document.createElement('img');
    img.className = 'media';
    const svg = encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}'><rect width='${w}' height='${h}' fill='${color}'/></svg>`);
    img.src = `data:image/svg+xml;utf8,${svg}`;
    img.alt = 'inline image';
    // Ensure no forced transform
    img.style.transform = 'none';
    img.onload = () => {
      // preserve aspect ratio and clamp
      const naturalRatio = img.naturalWidth / img.naturalHeight;
      const maxWidth = Math.min(320, chat.clientWidth * 0.6);
      const width = Math.min(img.naturalWidth, maxWidth);
      img.style.width = width + 'px';
      img.style.height = (width / naturalRatio) + 'px';
      img.style.maxHeight = '60vh';
    };
    return img;
  }

  function createMessage(side, content) {
    const msg = document.createElement('div');
    msg.className = `message ${side}`;
    msg.id = generateId('msg');
    msg.setAttribute('role', 'listitem');
    msg.setAttribute('aria-label', 'chat message');

    const avatar = createAvatar(side === 'left' ? '#4a90e2' : '#7b7b7b');
    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if (content && content.type === 'media') {
      bubble.appendChild(content.node);
    } else {
      bubble.innerText = content && content.text ? content.text : 'Random text message';
    }

    if (side === 'left') {
      msg.appendChild(avatar);
      msg.appendChild(bubble);
    } else {
      msg.appendChild(avatar);
      msg.appendChild(bubble);
    }

    return msg;
  }

  // Insert with scroll preservation: if inserting at top, adjust scrollTop by new height.
  function insertAtTop(node) {
    const previousScrollTop = chat.scrollTop;
    const previousScrollHeight = chat.scrollHeight;
    const beforeFirst = chat.children[0];
    chat.insertBefore(node, beforeFirst);
    // calculate added height and adjust scrollTop so content doesn't jump
    const added = chat.scrollHeight - previousScrollHeight;
    chat.scrollTop = previousScrollTop + added;
  }

  function insertAtBottom(node) {
    const wasAtBottom = (chat.scrollHeight - chat.scrollTop - chat.clientHeight) <= 1;
    chat.appendChild(node);
    if (wasAtBottom) {
      // scroll to bottom
      chat.scrollTop = chat.scrollHeight;
    }
  }

  function simulateInsertOnce() {
    // randomly insert header or message, sometimes at top
    const action = Math.random();
    if (action < 0.3) {
      const hdr = createTimeHeaderNode(createTimeHeaderLabel());
      insertAtTop(hdr);
      return {type:'header', id: hdr.id};
    } else {
      const side = Math.random() > 0.5 ? 'left' : 'right';
      let content;
      if (Math.random() > 0.6) {
        // random tall/wide image
        const w = Math.floor(Math.random() * 200 + 150);
        const h = Math.floor(Math.random() * 200 + 100);
        const color = w > h ? '#c0c0c0' : '#d0d0d0';
        const media = createMediaImage(w,h,color);
        content = {type:'media', node: media};
      } else {
        content = {text: 'Random text message ' + Math.floor(Math.random() * 100)};
      }
      const msg = createMessage(side, content);
      insertAtBottom(msg);
      return {type:'message', id: msg.id};
    }
  }

  // Expose for tests
  window.simulateInsertOnce = simulateInsertOnce;

  btn.addEventListener('click', () => {
    let scrollCount = 0;
    function fastScroll() {
      chat.scrollTop = (scrollCount % 2 === 0) ? chat.scrollHeight : 0;
      scrollCount++;
      if (scrollCount < 20) {
        requestAnimationFrame(fastScroll);
      } else {
        // do a few insertions
        for (let i=0;i<6;i++) {
          simulateInsertOnce();
        }
      }
    }
    fastScroll();
  });

})();
