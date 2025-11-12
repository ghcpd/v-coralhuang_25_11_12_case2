const chat = document.getElementById('chat');
const btn = document.getElementById('simulate');

// Track header IDs to ensure uniqueness
let headerIdCounter = 1;

// Preserve scroll position during DOM updates
function preserveScrollPosition(callback) {
  const scrollTop = chat.scrollTop;
  const scrollHeight = chat.scrollHeight;
  const clientHeight = chat.clientHeight;
  const wasAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
  
  callback();
  
  if (wasAtBottom) {
    // If user was at bottom, scroll to new bottom
    requestAnimationFrame(() => {
      chat.scrollTop = chat.scrollHeight;
    });
  } else {
    // Otherwise, maintain relative scroll position
    const newScrollHeight = chat.scrollHeight;
    const heightDiff = newScrollHeight - scrollHeight;
    chat.scrollTop = scrollTop + heightDiff;
  }
}

btn.onclick = () => {
  // use requestAnimationFrame for continuous fast scroll simulation
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

// Fixed: Proper DOM updates with unique IDs, no full rewrites, scroll preservation
function injectNewContent() {
  preserveScrollPosition(() => {
    // Create time header with unique ID
    const header = document.createElement('div');
    header.className = 'time-header';
    header.id = `header-${headerIdCounter++}`;
    header.setAttribute('role', 'separator');
    const timeStr = '09:' + (Math.floor(Math.random() * 60)).toString().padStart(2, '0') + ' AM';
    header.innerText = timeStr;
    header.setAttribute('aria-label', timeStr);
    
    // Insert header at the beginning
    chat.insertBefore(header, chat.firstChild);

    // Create message
    const msg = document.createElement('div');
    msg.className = (Math.random() > 0.5) ? 'message left' : 'message right';
    msg.setAttribute('role', 'article');
    msg.setAttribute('aria-label', 'Message');

    // Create avatar with proper alt text
    const avatar = document.createElement('img');
    avatar.className = 'avatar';
    avatar.src = 'https://i.pravatar.cc/40?img=' + Math.floor(Math.random() * 10 + 1);
    avatar.alt = 'User avatar';
    avatar.setAttribute('loading', 'lazy');

    // Create message content wrapper
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (Math.random() > 0.5) {
      // Add image with proper aspect ratio handling
      const img = document.createElement('img');
      img.className = 'media';
      const w = Math.floor(Math.random() * 200 + 150);
      const h = Math.floor(Math.random() * 400 + 200);
      img.src = `https://picsum.photos/${w}/${h}`;
      img.alt = 'Shared image';
      img.setAttribute('loading', 'lazy');
      
      // Wait for image to load, then ensure proper aspect ratio
      img.onload = function() {
        // Use natural dimensions to maintain aspect ratio
        if (img.naturalWidth && img.naturalHeight) {
          const aspectRatio = img.naturalWidth / img.naturalHeight;
          // Set max-width based on container, height auto maintains ratio
          img.style.maxWidth = '100%';
          img.style.height = 'auto';
        }
      };
      
      contentDiv.appendChild(img);
    } else {
      const textNode = document.createTextNode('Random text message ' + Math.floor(Math.random() * 100));
      contentDiv.appendChild(textNode);
    }

    // Assemble message
    // For both left and right, append avatar then content
    // CSS flex-direction: row-reverse handles visual reversal for right messages
    msg.appendChild(avatar);
    msg.appendChild(contentDiv);

    // Append message to chat
    chat.appendChild(msg);
    
    // Removed: chat.innerHTML += ''; (this was causing full DOM rewrite)
  });
}

// Expose function for testing
if (typeof window !== 'undefined') {
  window.simulateInsertOnce = function() {
    injectNewContent();
  };
}

