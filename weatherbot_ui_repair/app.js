// app.js - minimal DOM updates, stable headers, scroll anchor preservation, and image fixes
(function(){
  const messageList = document.getElementById('message-list');

  // initial messages dataset (id stable via timestamp)
  const messages = [
    {id: 't-2025-11-12-01', time: '2025-11-12 01:00', text:'Welcome to WeatherBot!'},
    {id: 't-2025-11-12-08', time: '2025-11-12 08:30', text:'Forecast ready for your region.'},
  ];

  function createTimeHeader(key, text){
    let el = document.getElementById(key);
    if(el) return el;
    el = document.createElement('div');
    el.id = key;
    el.className = 'time-header';
    el.setAttribute('role', 'separator');
    el.textContent = text;
    return el;
  }

  function createMessageNode(msg){
    const msgWrap = document.createElement('div');
    msgWrap.className = 'message';
    msgWrap.dataset.id = msg.id;
    msgWrap.dataset.side = msg.side || 'left';
    msgWrap.setAttribute('role', 'article');
    msgWrap.setAttribute('aria-label', `Message at ${msg.time}`);

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = msg.avatar || 'WB';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if(msg.image){
      const mediaWrap = document.createElement('div');
      mediaWrap.className = 'media';
      const img = document.createElement('img');
      img.src = msg.image.src;
      img.alt = msg.image.alt || 'Weather image';
      // ensure we do not apply rotation; remove any style that might attempt to transform
      img.style.transform = 'none';
      // constrain by natural size
      img.onload = function(){
        const ratio = img.naturalWidth / img.naturalHeight;
        if(ratio < 0.4){
          img.style.maxWidth = '60%';
        }
      }
      mediaWrap.appendChild(img);
      bubble.appendChild(mediaWrap);
    }

    if(msg.text){
      const p = document.createElement('p');
      p.textContent = msg.text;
      bubble.appendChild(p);
    }

    // minimal DOM placement - avatar and content
    msgWrap.appendChild(avatar);
    msgWrap.appendChild(bubble);
    return msgWrap;
  }

  function appendMessages(msgArray){
    // insert with minimal DOM changes; group by time header
    msgArray.forEach(msg => {
      const key = 'time-' + msg.id;
      let header = document.getElementById(key);
      if(!header){
        header = createTimeHeader(key, msg.time);
        messageList.appendChild(header);
      }
      const node = createMessageNode(msg);
      messageList.appendChild(node);
    });
  }

  function preserveScrollAnchor(fn){
    const listRect = messageList.getBoundingClientRect();
    // find first element visible inside the message list viewport
    const anchor = Array.from(messageList.children).find(ch => {
      const rect = ch.getBoundingClientRect();
      return rect.top < listRect.bottom && rect.bottom > listRect.top;
    });
    let anchorRect;
    if(anchor){ anchorRect = anchor.getBoundingClientRect(); }
    const prevScroll = messageList.scrollTop;
    fn();
    // After changes, adjust scroll to keep the anchor in the same relative position
    if(anchor){
      const newRect = anchor.getBoundingClientRect();
      const delta = newRect.top - anchorRect.top;
      messageList.scrollTop = prevScroll + delta;
    }
  }

  // expose simulation function used by validator: single incremental insert
  window.simulateInsertOnce = function(){
    preserveScrollAnchor(()=>{
      const ts = Date.now();
      const headerKey = 'time-' + ts;
      const header = createTimeHeader(headerKey, (new Date()).toLocaleString());
      messageList.insertBefore(header, messageList.firstChild);
      const msg = {id: 'm-'+ts, time: (new Date()).toLocaleString(), text: 'New message arrived ' + ts, avatar: 'NB'};
      const node = createMessageNode(msg);
      messageList.insertBefore(node, header.nextSibling);
    });
  }

  // startup: add initial content
  document.addEventListener('DOMContentLoaded', ()=>{
    appendMessages(messages);

    // add sample local images (svg data URIs) for validation tests
    const imgs = [
      {src: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300"><rect width="600" height="300" fill="#88c"/></svg>', alt:'landscape'},
      {src: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="300" height="800"><rect width="300" height="800" fill="#c88"/></svg>', alt:'tall'},
      {src: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500"><rect width="500" height="500" fill="#8c8"/></svg>', alt:'square'}
    ];
    // create messages that contain media elements.
    const m1 = {id:'m-img1', time:'2025-11-12 09:00', text:'A landscape image', avatar:'IM', image:imgs[0]};
    const m2 = {id:'m-img2', time:'2025-11-12 09:05', text:'A tall image', avatar:'IM', image:imgs[1]};
    const m3 = {id:'m-img3', time:'2025-11-12 09:06', text:'A square image', avatar:'IM', image:imgs[2]};
    appendMessages([m1,m2,m3]);
  });
})();
