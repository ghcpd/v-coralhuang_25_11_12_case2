// chatUI module: safe DOM updates, stable headers, anchored avatars, aspect-ratio-safe media
(function (global) {
  const container = document.getElementById('chat');
  const state = { headerCounter: 0, msgCounter: 0, headers: new Map() };

  function uniqueId(prefix) { return prefix + '-' + (Date.now().toString(36)) + '-' + (Math.random().toString(36).slice(2,6)); }

  function svgDataUrlAvatar(color, initials) {
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48'><rect width='100%' height='100%' fill='${color}' rx='50%'/><text x='50%' y='52%' font-size='20' text-anchor='middle' fill='white' font-family='system-ui'>${initials || ''}</text></svg>`;
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }

  function svgDataUrlMedia(w, h, bg) {
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}' viewBox='0 0 ${w} ${h}'><rect width='100%' height='100%' fill='${bg}'/><text x='50%' y='50%' font-size='20' text-anchor='middle' fill='white' font-family='system-ui'>${w}×${h}</text></svg>`;
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }

  // preserve relative scroll position or auto-scroll if near bottom
  function preserveScrollAndInsert(insertAction) {
    const nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 60;
    const beforeScrollHeight = container.scrollHeight;
    insertAction();
    // minimal DOM change – if user was at bottom, keep them at bottom, else preserve offset
    if (nearBottom) container.scrollTop = container.scrollHeight;
    else {
      // keep previous scrolled content in view
      const growth = container.scrollHeight - beforeScrollHeight;
      container.scrollTop = container.scrollTop + growth; // preserve viewport
    }
  }

  function addTimeHeader(text, id) {
    id = id || uniqueId('th');
    if (state.headers.has(id)) return id; // already exists
    const node = document.createElement('div');
    node.className = 'time-header';
    node.id = id;
    node.setAttribute('role', 'separator');
    node.textContent = text;
    // Keep headers at top of content logically – append then move to stable position at firstChild
    preserveScrollAndInsert(() => container.insertBefore(node, container.firstChild));
    state.headers.set(id, node);
    return id;
  }

  function appendMessage(spec) {
    // spec: {side, text, media:{w,h}, avatarColor}
    const id = uniqueId('msg');
    const side = spec.side === 'right' ? 'right' : 'left';
    const bubble = document.createElement('div');
    bubble.className = `message ${side}`;
    bubble.id = id;
    bubble.setAttribute('role', 'article');
    bubble.tabIndex = 0;

    const avatar = document.createElement('img');
    avatar.className = 'avatar';
    const initials = (spec.text || '').split(' ').slice(0,2).map(s=>s[0]).join('').slice(0,2).toUpperCase() || 'U';
    avatar.src = svgDataUrlAvatar(spec.avatarColor || '#888', initials);
    avatar.alt = 'User avatar';

    const body = document.createElement('div');
    body.className = 'message-body';

    if (spec.media) {
      const img = document.createElement('img');
      img.className = 'media';
      // place a data URL based on requested dims
      const w = spec.media.w || 320;
      const h = spec.media.h || 240;
      const bg = '#8b6';
      img.src = svgDataUrlMedia(w, h, bg);
      img.alt = `Image ${w}x${h}`;
      // ensure natural dims are available after load for validators
      img.dataset.naturalW = w;
      img.dataset.naturalH = h;
      body.appendChild(img);
    } else if (spec.text) {
      const t = document.createElement('div');
      t.textContent = spec.text;
      body.appendChild(t);
    }

    // layout: avatar + body
    // For left: avatar + body; for right: row-reverse via CSS
    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.appendChild(avatar);
    meta.appendChild(body);
    bubble.appendChild(meta);

    preserveScrollAndInsert(() => container.appendChild(bubble));
    state.msgCounter++;
    return id;
  }

  // Public helpers for validator or external usage
  global.chatUI = {
    appendMessage, addTimeHeader, containerRef: container,
    getMessageRects: function () {
      const rects = [];
      const nodeList = container.querySelectorAll('.message');
      nodeList.forEach(n => rects.push({ id: n.id, rect: n.getBoundingClientRect(), visible: isVisible(n) }));
      return rects;
    }
  };

  function isVisible(el) {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && r.bottom >= 0 && r.top <= (document.documentElement.clientHeight || window.innerHeight);
  }

})(window);

// keep a light global warning for debugging
console.info('Chat UI (fixed) loaded');
