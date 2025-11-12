// app.js - fixes for chat UI interactions & stable updates
(function (){
  const chatBody = document.getElementById('chat-body');
  const simulate = document.getElementById('simulate');
  const announcer = document.getElementById('chat-announcer');

  // simple deterministic color palette for avatars
  const palette = ['#6A90FF','#7eb77b','#c472ff','#ff7e6a','#ffd76a','#78d6e1'];

  function svgAvatar(color, text) {
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'><rect width='100%' height='100%' fill='${color}' rx='40'/><text x='50%' y='55%' font-size='34' font-weight='600' text-anchor='middle' fill='white' font-family='system-ui, Arial, sans-serif'>${text}</text></svg>`;
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
  }

  function svgPlaceholder(w,h,text){
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}' viewBox='0 0 ${w} ${h}'><defs><linearGradient id='g' x1='0' x2='1'><stop offset='0' stop-color='#efefef'/><stop offset='1' stop-color='#eee'/></linearGradient></defs><rect width='100%' height='100%' fill='url(%23g)'/><g fill='#ccc' font-size='20' font-family='system-ui, Arial, sans-serif' text-anchor='middle'><text x='50%' y='50%'>${text}</text></g></svg>`;
    return {uri:`data:image/svg+xml;utf8,${encodeURIComponent(svg)}`, w, h};
  }

  // utility to create a message node
  function createMessage({side='left', text='', avatarSeed=0, media}){
    const row = document.createElement('div');
    row.className = 'message-row';
    const msg = document.createElement('article');
    msg.className = 'message ' + side;
    msg.setAttribute('role','article');

    const avatarImg = document.createElement('img');
    avatarImg.className = 'avatar';
    avatarImg.alt = `User avatar`;
    avatarImg.src = svgAvatar(palette[avatarSeed % palette.length], String.fromCharCode(65+avatarSeed));
    msg.appendChild(avatarImg);

    if (media) {
      const wrap = document.createElement('div');
      wrap.className = 'media-wrap bubble';
      const img = document.createElement('img');
      img.alt = media.title || 'shared media';
      img.decoding = 'async';
      img.src = media.uri;
      img.width = media.w;
      img.height = media.h;
      wrap.appendChild(img);
      msg.appendChild(wrap);
    } else {
      const bubble = document.createElement('div');
      bubble.className = 'bubble';
      bubble.innerHTML = `<div>${escapeHtml(text)}</div>`;
      msg.appendChild(bubble);
    }
    row.appendChild(msg);
    return row;
  }

  // escape to avoid accidental HTML injection in text nodes (small helper)
  function escapeHtml(s){
    return String(s)
      .replace(/&/g,'&amp;')
      .replace(/</g,'&lt;')
      .replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;');
  }

  // preserve scroll anchor: when adding to top, keep previous visible area stable; when adding to bottom, optionally keep bottom if user is at bottom
  function preserveScrollAnchor(beforeHeight, beforeTop, isTopInsertion){
    // after updating, adjust scrollTop to maintain previous visible content
    // Only adjust if the update was inserted at the top; appending at the bottom should not affect scrollTop (for a user at the top)
    if (!isTopInsertion) return;
    const delta = chatBody.scrollHeight - beforeHeight;
    // if the user is not at bottom (scrollTop != scrollHeight - clientHeight), preserve previous viewport location
    if (Math.abs((beforeTop + chatBody.clientHeight) - beforeHeight) > 5) {
      chatBody.scrollTop = beforeTop + delta;
    }
  }

  // global header registry to avoid duplicates
  const headers = new Set();
  function insertTimeHeader(ts){
    if (headers.has(ts)) return;
    headers.add(ts);
    const header = document.createElement('div');
    header.className = 'time-header';
    header.innerText = ts;
    header.id = `time-${Math.random().toString(36).slice(2,9)}`;
    header.setAttribute('role','separator');

    // when inserting to top, maintain anchor
    const beforeHeight = chatBody.scrollHeight;
    const beforeTop = chatBody.scrollTop;
    chatBody.insertBefore(header, chatBody.firstChild);
    preserveScrollAnchor(beforeHeight, beforeTop, true);
  }

  // a function to add a new message, with stabilized DOM operations
  function injectNewContent(options={toTop:false}){
    // avoid heavy DOM mutations by creating nodes in a fragment
    const frag = document.createDocumentFragment();
    const beforeHeight = chatBody.scrollHeight;
    const beforeTop = chatBody.scrollTop;

    // random header/time and message
    const dt = new Date();
    const min = String(Math.floor(Math.random()*60)).padStart(2,'0');
    const ts = `09:${min} AM`;
    if (options.addTime) {
      const header = document.createElement('div');
      header.className = 'time-header';
      header.innerText = ts;
      header.id = `time-${Math.random().toString(36).slice(2,9)}`;
      header.setAttribute('role','separator');
      frag.appendChild(header);
    }

    const side = (Math.random()>0.5) ? 'left' : 'right';

    let media = null;
    if (Math.random()>0.5) {
      const w = Math.floor(Math.random()*300 + 120);
      const h = Math.floor(Math.random()*300 + 120);
      const placeholder = svgPlaceholder(w,h,`${w}×${h}`);
      media = {uri: placeholder.uri, w, h, title: placeholder.w+'×'+placeholder.h};
    }

    const msg = createMessage({side, text:`Random text message ${Math.floor(Math.random()*100)}`, avatarSeed: Math.floor(Math.random()*10), media});
    frag.appendChild(msg);

    if (options.toTop) {
      chatBody.insertBefore(frag, chatBody.firstChild);
    } else {
      chatBody.appendChild(frag);
    }

    preserveScrollAnchor(beforeHeight, beforeTop, !!options.toTop);
    announcer.textContent = 'New activity';
  }

  // populate initial content
  function seedInitial(){
    const payload = [
      {side:'left', text:'Hey! How are you doing today?', avatarSeed:1},
      {side:'right', text:`I'm good! Working on that new UI layout.`, avatarSeed:2},
      {side:'left', avatarSeed:3, media: svgPlaceholder(260,560,'260×560')},
      {side:'right', text:'Cool, send me screenshots later.', avatarSeed:4}
    ];
    payload.forEach(p => {
      const node = createMessage(p);
      chatBody.appendChild(node);
    });
  }

  // wire up the fast scroll simulation using RAF
  simulate.addEventListener('click', ()=>{
    let curs = 0; let toggles = 0;
    function loop() {
      chatBody.scrollTop = (toggles % 2 === 0) ? chatBody.scrollHeight : 0;
      toggles++;
      if (toggles < 20) requestAnimationFrame(loop);
      else {
        injectNewContent({addTime:true});
      }
    }
    loop();
  });

  // expose a small function for tests to call repeatedly
  window.simulateInsertOnce = function() {
    // By default, simulate an insertion to the bottom so it doesn't jump the viewport while tests run.
    // record location for tests/debuggers
    window.lastInsertionLocation = 'bottom';
    injectNewContent({addTime:true, toTop: false});
  }

  seedInitial();
})();
