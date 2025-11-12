// Fixed: Proper DOM manipulation with scroll preservation and stable IDs
let messageCounter = 4; // Start at 4 since HTML has message-0 through message-3
let headerCounter = 1; // Start at 1 since HTML has time-header-0

const chat = document.getElementById('chat');
const btn = document.getElementById('simulate');

// Fixed: Preserve scroll position during DOM updates
function preserveScrollPosition(callback) {
  const scrollTop = chat.scrollTop;
  const scrollHeight = chat.scrollHeight;
  callback();
  const newScrollHeight = chat.scrollHeight;
  const heightDiff = newScrollHeight - scrollHeight;
  chat.scrollTop = scrollTop + heightDiff;
}

// Fixed: Create stable time header with unique ID
function createTimeHeader(timeText) {
  const header = document.createElement('div');
  header.className = 'time-header';
  header.setAttribute('role', 'separator');
  header.setAttribute('aria-label', `Time: ${timeText}`);
  header.id = `time-header-${headerCounter++}`;
  header.textContent = timeText;
  return header;
}

// Fixed: Create message with proper structure and accessibility
function createMessage(isLeft, avatarSrc, content) {
  const msg = document.createElement('div');
  msg.className = isLeft ? 'message left' : 'message right';
  msg.id = `message-${messageCounter++}`;
  msg.setAttribute('role', 'article');
  
  const avatar = document.createElement('img');
  avatar.className = 'avatar';
  avatar.src = avatarSrc;
  avatar.alt = isLeft ? 'Sender avatar' : 'Your avatar';
  avatar.setAttribute('aria-hidden', 'true');
  
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  
  if (typeof content === 'string') {
    contentDiv.textContent = content;
  } else if (content instanceof HTMLElement) {
    contentDiv.appendChild(content);
  } else {
    contentDiv.appendChild(content);
  }
  
  msg.appendChild(avatar);
  msg.appendChild(contentDiv);
  
  return msg;
}

// Fixed: Create media image with proper aspect ratio handling
function createMediaImage(src, width, height) {
  const img = document.createElement('img');
  img.className = 'media';
  img.src = src;
  img.alt = 'Shared image';
  img.loading = 'lazy';
  
  // Set max-width based on container, preserve aspect ratio
  img.style.maxWidth = '100%';
  img.style.height = 'auto';
  img.style.maxHeight = '400px';
  
  // Wait for image to load to get natural dimensions
  img.onload = function() {
    const naturalRatio = img.naturalWidth / img.naturalHeight;
    const displayRatio = img.clientWidth / img.clientHeight;
    
    // If aspect ratio is off by more than 2%, adjust
    if (Math.abs(naturalRatio - displayRatio) > 0.02) {
      if (img.naturalWidth > img.naturalHeight) {
        // Landscape: constrain by width
        img.style.maxWidth = '100%';
        img.style.height = 'auto';
      } else {
        // Portrait: constrain by height
        img.style.maxHeight = '400px';
        img.style.width = 'auto';
      }
    }
  };
  
  return img;
}

// Fixed: Minimal DOM update without innerHTML rewrite
function injectNewContent() {
  preserveScrollPosition(() => {
    const timeText = '09:' + Math.floor(Math.random() * 60).toString().padStart(2, '0') + ' AM';
    const header = createTimeHeader(timeText);
    chat.insertBefore(header, chat.firstChild);
    
    const isLeft = Math.random() > 0.5;
    const avatarSrc = 'https://i.pravatar.cc/40?img=' + Math.floor(Math.random() * 10 + 1);
    
    let content;
    if (Math.random() > 0.5) {
      const w = Math.floor(Math.random() * 200 + 150);
      const h = Math.floor(Math.random() * 400 + 200);
      const imgSrc = `https://picsum.photos/${w}/${h}`;
      content = createMediaImage(imgSrc, w, h);
    } else {
      content = 'Random text message ' + Math.floor(Math.random() * 100);
    }
    
    const msg = createMessage(isLeft, avatarSrc, content);
    chat.appendChild(msg);
  });
}

// Expose function for test validator
window.simulateInsertOnce = injectNewContent;

btn.onclick = () => {
  // Fixed: Simulate scroll without causing layout issues
  let scrollCount = 0;
  function fastScroll() {
    chat.scrollTop = (scrollCount % 2 === 0) ? chat.scrollHeight : 0;
    scrollCount++;
    if (scrollCount < 20) {
      requestAnimationFrame(fastScroll);
    } else {
      injectNewContent();
    }
  }
  fastScroll();
};

