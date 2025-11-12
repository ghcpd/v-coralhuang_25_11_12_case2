const chat = document.getElementById('chat');
const btn = document.getElementById('simulate');
let messageIdCounter = 100;
let headerIdCounter = 0;

// Track scroll position to restore after DOM updates
let scrollOffset = 0;

btn.onclick = () => {
  // FIX #3, #4: Smooth scroll without rapid reflow
  let scrollCount = 0;
  const startScroll = chat.scrollTop;
  
  function smoothScroll() {
    chat.scrollTop = startScroll + (scrollCount * 15);
    scrollCount++;
    if (scrollCount < 10 && chat.scrollTop < chat.scrollHeight - chat.clientHeight) {
      requestAnimationFrame(smoothScroll);
    } else {
      // Small delay before injecting to ensure layout is stable
      setTimeout(injectNewContent, 100);
    }
  }
  smoothScroll();
};

/**
 * FIX #3, #4: Inject new content with minimal DOM updates
 * - Uses stable IDs to prevent duplicate headers
 * - Appends to bottom instead of insertBefore
 * - Avoids full innerHTML rewrites
 * - Preserves scroll position
 */
function injectNewContent() {
  // Store scroll position
  const wasAtBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 50;
  
  // Create header with stable ID
  const headerId = `header-${headerIdCounter++}`;
  const header = document.createElement('div');
  header.id = headerId;
  header.className = 'time-header';
  header.setAttribute('role', 'separator');
  const hours = Math.floor(Math.random() * 24);
  const minutes = Math.floor(Math.random() * 60);
  header.innerText = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
  
  // Append header
  chat.appendChild(header);
  
  // Create message with unique ID
  const msgId = `msg-${messageIdCounter++}`;
  const msg = document.createElement('div');
  msg.id = msgId;
  msg.className = (Math.random() > 0.5) ? 'message left' : 'message right';
  msg.setAttribute('role', 'article');
  
  // Create avatar with alt text
  const avatar = document.createElement('img');
  avatar.className = 'avatar';
  const avatarNum = Math.floor(Math.random() * 10 + 1);
  avatar.src = `https://i.pravatar.cc/40?img=${avatarNum}`;
  avatar.alt = `User ${avatarNum} avatar`;
  msg.appendChild(avatar);
  
  // FIX #2: Add message content wrapper and optionally media
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  
  if (Math.random() > 0.5) {
    // Add text message
    contentDiv.textContent = 'Random text message ' + Math.floor(Math.random() * 1000);
    msg.appendChild(contentDiv);
  } else {
    // Add image with preserved aspect ratio
    const img = document.createElement('img');
    img.className = 'media';
    
    // Use fixed aspect ratios to prevent distortion
    const aspectRatios = ['200/150', '300/200', '250/250', '200/300'];
    const chosen = aspectRatios[Math.floor(Math.random() * aspectRatios.length)];
    img.src = `https://picsum.photos/${chosen}?random=${Math.random()}`;
    img.alt = 'Shared image';
    
    // FIX #2: Ensure no rotation transform is applied
    img.style.transform = 'none';
    img.style.objectFit = 'contain';
    
    msg.appendChild(img);
  }
  
  // Append message
  chat.appendChild(msg);
  
  // FIX #3: Restore scroll position if user was at bottom
  if (wasAtBottom) {
    requestAnimationFrame(() => {
      chat.scrollTop = chat.scrollHeight;
    });
  }
}

/**
 * Allow external test script to inject content for validation
 * Called by test_validator.py via Playwright
 */
window.simulateInsertOnce = function() {
  injectNewContent();
};

/**
 * Return layout info for validator
 */
window.getLayoutInfo = function() {
  const messages = Array.from(document.querySelectorAll('.message'));
  return messages.map((msg, i) => {
    const rect = msg.getBoundingClientRect();
    const avatar = msg.querySelector('.avatar');
    const media = msg.querySelector('.media');
    return {
      id: msg.id,
      index: i,
      top: rect.top,
      left: rect.left,
      right: rect.right,
      bottom: rect.bottom,
      width: rect.width,
      height: rect.height,
      hasAvatar: !!avatar,
      hasMedia: !!media,
      isAbsolute: window.getComputedStyle(msg).position === 'absolute',
      mediaRotation: media ? window.getComputedStyle(media).transform : null
    };
  });
};

/**
 * Check for overlap between elements
 */
window.checkOverlaps = function() {
  const messages = Array.from(document.querySelectorAll('.message'));
  const overlaps = [];
  
  for (let i = 0; i < messages.length; i++) {
    for (let j = i + 1; j < messages.length; j++) {
      const rect1 = messages[i].getBoundingClientRect();
      const rect2 = messages[j].getBoundingClientRect();
      
      // Check for overlap
      if (!(rect1.right < rect2.left || rect1.left > rect2.right ||
            rect1.bottom < rect2.top || rect1.top > rect2.bottom)) {
        overlaps.push({
          msg1: messages[i].id,
          msg2: messages[j].id,
          area: (Math.min(rect1.right, rect2.right) - Math.max(rect1.left, rect2.left)) *
                (Math.min(rect1.bottom, rect2.bottom) - Math.max(rect1.top, rect2.top))
        });
      }
    }
  }
  
  return overlaps;
};

/**
 * Check media aspect ratios
 */
window.checkMediaAspectRatios = function() {
  const medias = Array.from(document.querySelectorAll('.message img.media'));
  const ratios = [];
  
  medias.forEach(img => {
    const naturalRatio = img.naturalWidth / img.naturalHeight;
    const displayRatio = img.clientWidth / img.clientHeight;
    const diff = Math.abs((naturalRatio - displayRatio) / naturalRatio * 100);
    
    ratios.push({
      src: img.src,
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
      displayWidth: img.clientWidth,
      displayHeight: img.clientHeight,
      naturalRatio: naturalRatio.toFixed(3),
      displayRatio: displayRatio.toFixed(3),
      diffPercent: diff.toFixed(2),
      transform: window.getComputedStyle(img).transform,
      isWithinTolerance: diff <= 2
    });
  });
  
  return ratios;
};

/**
 * Check for duplicate IDs
 */
window.checkDuplicateIds = function() {
  const allIds = Array.from(document.querySelectorAll('[id]')).map(el => el.id);
  const counts = {};
  allIds.forEach(id => {
    counts[id] = (counts[id] || 0) + 1;
  });
  return Object.entries(counts).filter(([id, count]) => count > 1);
};

/**
 * Check accessibility attributes
 */
window.checkAccessibility = function() {
  const issues = [];
  
  // Check for images without alt text
  const images = Array.from(document.querySelectorAll('img'));
  images.forEach(img => {
    if (!img.alt || img.alt.trim() === '') {
      issues.push({
        type: 'missing-alt',
        element: img.className,
        src: img.src
      });
    }
  });
  
  // Check for messages without role or aria-label
  const messages = Array.from(document.querySelectorAll('.message'));
  messages.forEach(msg => {
    if (!msg.getAttribute('role')) {
      issues.push({
        type: 'missing-role',
        id: msg.id
      });
    }
  });
  
  // Check headers have separator role
  const headers = Array.from(document.querySelectorAll('.time-header'));
  headers.forEach(header => {
    if (!header.getAttribute('role')) {
      issues.push({
        type: 'missing-header-role',
        id: header.id
      });
    }
  });
  
  return {
    totalIssues: issues.length,
    issues: issues
  };
};
